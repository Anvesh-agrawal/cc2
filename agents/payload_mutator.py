"""
Payload Mutator Agent
=====================
Self-healing data engine that mutates transaction payloads to fix gateway-specific issues.
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import uuid
import re
import unicodedata

from config import ActionType, config


@dataclass
class MutationRule:
    """A learned rule for payload mutation."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    gateway: str = ""
    error_pattern: str = ""  # e.g., "E016_INVALID_ADDRESS"
    target_field: str = ""   # e.g., "address_line1"
    mutation_type: str = ""  # "remove_special", "truncate", "normalize_phone", etc.
    
    # Learning statistics
    success_count: int = 0
    failure_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now())
    last_used: datetime = field(default_factory=lambda: datetime.now())
    
    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.5
    
    @property
    def confidence(self) -> float:
        """Bayesian confidence based on sample size."""
        total = self.success_count + self.failure_count
        if total < 3:
            return 0.3  # Low confidence with few samples
        return min(0.95, 0.5 + (total / 20) * 0.45)


@dataclass
class MutationRecord:
    """Record of a payload mutation attempt."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    transaction_id: str = ""
    gateway: str = ""
    error_code: str = ""
    
    # What was mutated
    field_name: str = ""
    original_value: str = ""
    mutated_value: str = ""
    mutation_type: str = ""
    
    # Outcome
    timestamp: datetime = field(default_factory=lambda: datetime.now())
    was_successful: Optional[bool] = None
    outcome_recorded_at: Optional[datetime] = None
    
    # Rule used
    rule_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "transaction_id": self.transaction_id,
            "gateway": self.gateway,
            "error_code": self.error_code,
            "field_name": self.field_name,
            "original_value": self.original_value,
            "mutated_value": self.mutated_value,
            "mutation_type": self.mutation_type,
            "timestamp": self.timestamp,
            "was_successful": self.was_successful
        }


# Gateway-specific rules (simulated "unwritten rules")
GATEWAY_QUIRKS = {
    "razorpay": {
        "address_max_length": 50,
        "hates_special_chars": True,
        "name_ascii_only": False,
        "phone_digits_only": True
    },
    "paytm": {
        "address_max_length": 40,
        "hates_special_chars": True,
        "name_ascii_only": True,
        "phone_digits_only": True
    },
    "phonepe": {
        "address_max_length": 60,
        "hates_special_chars": False,
        "name_ascii_only": False,
        "phone_digits_only": True
    },
    "billdesk": {
        "address_max_length": 35,
        "hates_special_chars": True,
        "name_ascii_only": True,
        "phone_digits_only": True
    },
    "ccavenue": {
        "address_max_length": 45,
        "hates_special_chars": True,
        "name_ascii_only": False,
        "phone_digits_only": False
    }
}

# Error codes that indicate payload issues
PAYLOAD_ERROR_CODES = {
    "E016_INVALID_ADDRESS": "address_line1",
    "E017_INVALID_PHONE": "phone_number", 
    "E018_INVALID_NAME": "customer_name",
    "E019_FIELD_TOO_LONG": "address_line1"  # Most common for address
}


class PayloadMutatorAgent:
    """
    Agent that fixes transaction data for gateway compatibility.
    
    Implements the Payload Polymorphism pattern:
    - Observes transaction failures with payload-related errors
    - Identifies the problematic field and mutation needed
    - Mutates the payload and retries on the same gateway
    - Learns which mutations work for each gateway
    """
    
    def __init__(self):
        # Learned mutation rules
        self.rules: Dict[str, MutationRule] = {}
        
        # Recent mutations for tracking
        self.recent_mutations: List[MutationRecord] = []
        self.pending_mutations: Dict[str, MutationRecord] = {}  # id -> record
        
        # Statistics
        self.total_mutations = 0
        self.successful_mutations = 0
        self.failed_mutations = 0
        
        # Initialize default rules based on known gateway quirks
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Initialize default mutation rules based on gateway quirks."""
        for gateway, quirks in GATEWAY_QUIRKS.items():
            if quirks.get("hates_special_chars"):
                rule = MutationRule(
                    gateway=gateway,
                    error_pattern="E016_INVALID_ADDRESS",
                    target_field="address_line1",
                    mutation_type="remove_special",
                    success_count=3,  # Start with some prior
                    failure_count=1
                )
                self.rules[rule.id] = rule
            
            if quirks.get("name_ascii_only"):
                rule = MutationRule(
                    gateway=gateway,
                    error_pattern="E018_INVALID_NAME",
                    target_field="customer_name",
                    mutation_type="sanitize_name",
                    success_count=3,
                    failure_count=1
                )
                self.rules[rule.id] = rule
            
            if quirks.get("phone_digits_only"):
                rule = MutationRule(
                    gateway=gateway,
                    error_pattern="E017_INVALID_PHONE",
                    target_field="phone_number",
                    mutation_type="normalize_phone",
                    success_count=4,
                    failure_count=1
                )
                self.rules[rule.id] = rule
    
    def can_mutate(self, error_code: str, gateway: str) -> bool:
        """Check if we can attempt a mutation for this error."""
        return error_code in PAYLOAD_ERROR_CODES
    
    def get_applicable_rule(self, error_code: str, gateway: str) -> Optional[MutationRule]:
        """Find the best mutation rule for this error and gateway."""
        applicable_rules = [
            rule for rule in self.rules.values()
            if rule.gateway == gateway and rule.error_pattern == error_code
        ]
        
        if not applicable_rules:
            # Try to create a new rule based on error type
            return self._create_rule_for_error(error_code, gateway)
        
        # Return the rule with highest success rate
        return max(applicable_rules, key=lambda r: r.success_rate * r.confidence)
    
    def _create_rule_for_error(self, error_code: str, gateway: str) -> Optional[MutationRule]:
        """Create a new mutation rule for an unknown error pattern."""
        target_field = PAYLOAD_ERROR_CODES.get(error_code)
        if not target_field:
            return None
        
        # Determine mutation type based on error and field
        mutation_type = self._infer_mutation_type(error_code, target_field, gateway)
        
        rule = MutationRule(
            gateway=gateway,
            error_pattern=error_code,
            target_field=target_field,
            mutation_type=mutation_type
        )
        self.rules[rule.id] = rule
        return rule
    
    def _infer_mutation_type(self, error_code: str, field: str, gateway: str) -> str:
        """Infer the best mutation type for an error."""
        if error_code == "E016_INVALID_ADDRESS":
            quirks = GATEWAY_QUIRKS.get(gateway, {})
            if quirks.get("hates_special_chars"):
                return "remove_special"
            return "truncate"
        elif error_code == "E017_INVALID_PHONE":
            return "normalize_phone"
        elif error_code == "E018_INVALID_NAME":
            return "sanitize_name"
        elif error_code == "E019_FIELD_TOO_LONG":
            return "truncate"
        return "remove_special"  # Default
    
    def mutate_payload(
        self,
        transaction_id: str,
        gateway: str,
        error_code: str,
        payload: Dict[str, str]
    ) -> Tuple[Dict[str, str], Optional[MutationRecord]]:
        """
        Mutate the transaction payload to fix the error.
        
        Returns:
            Tuple of (mutated_payload, mutation_record)
        """
        rule = self.get_applicable_rule(error_code, gateway)
        if not rule:
            return payload, None
        
        target_field = rule.target_field
        if target_field not in payload or not payload[target_field]:
            return payload, None
        
        original_value = payload[target_field]
        mutated_value = self._apply_mutation(original_value, rule.mutation_type, gateway)
        
        if mutated_value == original_value:
            return payload, None
        
        # Create mutation record
        record = MutationRecord(
            transaction_id=transaction_id,
            gateway=gateway,
            error_code=error_code,
            field_name=target_field,
            original_value=original_value,
            mutated_value=mutated_value,
            mutation_type=rule.mutation_type,
            rule_id=rule.id
        )
        
        # Update tracking
        self.pending_mutations[record.id] = record
        self.total_mutations += 1
        rule.last_used = datetime.now()
        
        # Create mutated payload
        mutated_payload = payload.copy()
        mutated_payload[target_field] = mutated_value
        
        return mutated_payload, record
    
    def _apply_mutation(self, value: str, mutation_type: str, gateway: str) -> str:
        """Apply a specific mutation to a value."""
        if mutation_type == "remove_special":
            # Remove special characters like #, @, &, etc.
            return re.sub(r'[#@&%$!*(){}[\]|\\<>]', '', value).strip()
        
        elif mutation_type == "truncate":
            max_length = GATEWAY_QUIRKS.get(gateway, {}).get("address_max_length", 50)
            if len(value) > max_length:
                return value[:max_length-3] + "..."
            return value
        
        elif mutation_type == "normalize_phone":
            # Extract only digits, remove country code prefixes
            digits = re.sub(r'\D', '', value)
            if len(digits) > 10 and digits.startswith("91"):
                digits = digits[2:]  # Remove India country code
            return digits[-10:] if len(digits) >= 10 else digits
        
        elif mutation_type == "sanitize_name":
            # Convert to ASCII-safe version
            normalized = unicodedata.normalize('NFKD', value)
            ascii_safe = normalized.encode('ascii', 'ignore').decode('ascii')
            return ascii_safe.strip()
        
        elif mutation_type == "fix_pincode":
            # Remove spaces from pincode
            return re.sub(r'\s', '', value)
        
        return value
    
    def record_outcome(self, mutation_id: str, was_successful: bool):
        """Record the outcome of a mutation attempt."""
        record = self.pending_mutations.pop(mutation_id, None)
        if not record:
            return
        
        record.was_successful = was_successful
        record.outcome_recorded_at = datetime.now()
        
        # Update statistics
        if was_successful:
            self.successful_mutations += 1
        else:
            self.failed_mutations += 1
        
        # Update rule learning
        if record.rule_id and record.rule_id in self.rules:
            rule = self.rules[record.rule_id]
            if was_successful:
                rule.success_count += 1
            else:
                rule.failure_count += 1
        
        # Store in recent mutations
        self.recent_mutations.append(record)
        if len(self.recent_mutations) > 100:
            self.recent_mutations = self.recent_mutations[-100:]
    
    def get_recent_mutations(self, limit: int = 10) -> List[Dict]:
        """Get recent mutations with their outcomes."""
        recent = sorted(
            self.recent_mutations,
            key=lambda m: m.timestamp,
            reverse=True
        )[:limit]
        return [m.to_dict() for m in recent]
    
    def get_stats(self) -> Dict:
        """Get mutation statistics."""
        success_rate = (
            self.successful_mutations / self.total_mutations
            if self.total_mutations > 0 else 0.0
        )
        
        return {
            "total_mutations": self.total_mutations,
            "successful_mutations": self.successful_mutations,
            "failed_mutations": self.failed_mutations,
            "success_rate": success_rate,
            "active_rules": len(self.rules),
            "pending_outcomes": len(self.pending_mutations)
        }
    
    def get_rules_by_gateway(self, gateway: str) -> List[Dict]:
        """Get learned rules for a specific gateway."""
        rules = [
            {
                "id": rule.id,
                "error_pattern": rule.error_pattern,
                "target_field": rule.target_field,
                "mutation_type": rule.mutation_type,
                "success_rate": rule.success_rate,
                "confidence": rule.confidence,
                "total_uses": rule.success_count + rule.failure_count
            }
            for rule in self.rules.values()
            if rule.gateway == gateway
        ]
        return sorted(rules, key=lambda r: r["success_rate"], reverse=True)
