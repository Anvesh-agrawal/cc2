"""
Payment Simulator
=================
Generates realistic, chaotic payment data streams for testing and demonstration.
"""

import random
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import threading
import time

from config import (
    PaymentMethod, TransactionStatus, SimulationConfig, config
)
from models.transaction import Transaction


@dataclass
class ChaosScenario:
    """A chaos scenario affecting payment simulation."""
    name: str
    description: str
    affected_entity: str  # Bank, method, or "all"
    entity_type: str      # "bank", "method", "gateway", "region"
    
    # Impact
    success_rate_modifier: float = 1.0  # Multiplier (0.5 = 50% reduction)
    latency_modifier: float = 1.0       # Multiplier (2.0 = 2x latency)
    error_code_override: Optional[str] = None
    
    # Duration
    start_time: datetime = field(default_factory=datetime.now)
    duration_seconds: int = 300  # 5 minutes default
    
    # Probability of affecting each transaction
    impact_probability: float = 0.8
    
    @property
    def is_active(self) -> bool:
        elapsed = (datetime.now() - self.start_time).total_seconds()
        return elapsed < self.duration_seconds
    
    @property
    def remaining_seconds(self) -> float:
        elapsed = (datetime.now() - self.start_time).total_seconds()
        return max(0, self.duration_seconds - elapsed)


class PaymentSimulator:
    """
    Simulates realistic payment transaction streams with configurable chaos.
    
    Features:
    - Multiple payment methods with different characteristics
    - Bank/issuer simulation with varying performance
    - Chaos scenarios (degradation, storms, spikes)
    - Realistic error code distribution
    """
    
    def __init__(self, config: SimulationConfig = None):
        self.config = config or SimulationConfig()
        self.active_scenarios: List[ChaosScenario] = []
        self.transaction_counter = 0
        self.running = False
        self._lock = threading.Lock()
        
        # Gateways
        self.gateways = ["razorpay", "paytm", "phonepe", "billdesk", "ccavenue"]
        
        # Merchants
        self.merchants = [f"MERCH_{i:04d}" for i in range(1, 51)]
        
        # Regions
        self.regions = ["IN-MH", "IN-DL", "IN-KA", "IN-TN", "IN-WB", "IN-GJ"]
        
        # Pre-defined chaos templates
        self.chaos_templates = {
            "issuer_degradation": self._create_issuer_degradation,
            "retry_storm": self._create_retry_storm,
            "method_fatigue": self._create_method_fatigue,
            "latency_spike": self._create_latency_spike,
            "gateway_issues": self._create_gateway_issues,
            "peak_hour_load": self._create_peak_hour_load,
        }
        
        # Track retry history for retry storm simulation
        self.pending_retries: List[Tuple[Transaction, int]] = []  # (original_txn, retry_attempt)
    
    def generate_transaction(self) -> Transaction:
        """Generate a single transaction with current chaos effects applied."""
        with self._lock:
            self.transaction_counter += 1
            
            # Check for pending retries first
            if self.pending_retries and random.random() < 0.3:
                original, attempt = self.pending_retries.pop(0)
                return self._generate_retry(original, attempt)
            
            # Select random attributes
            payment_method = random.choice(list(PaymentMethod))
            issuer_bank = random.choice(self.config.banks)
            gateway = random.choice(self.gateways)
            merchant = random.choice(self.merchants)
            region = random.choice(self.regions)
            
            # Generate base success probability
            base_success = self.config.base_success_rates.get(
                payment_method.value, 0.9
            )
            
            # Apply chaos scenarios
            success_prob, latency_mod, error_override = self._apply_chaos(
                issuer_bank, payment_method, gateway, region
            )
            success_prob *= base_success
            
            # Determine outcome
            is_success = random.random() < success_prob
            status = TransactionStatus.SUCCESS if is_success else TransactionStatus.FAILURE
            
            # Generate latency
            base_latency_mean, base_latency_std = self.config.base_latency.get(
                payment_method.value, (1000, 300)
            )
            latency = max(50, np.random.normal(
                base_latency_mean * latency_mod,
                base_latency_std * latency_mod
            ))
            
            # Handle timeout
            if latency > 30000:  # 30 second timeout
                status = TransactionStatus.TIMEOUT
                latency = 30000
            
            # Error code for failures
            error_code = None
            error_message = None
            if status != TransactionStatus.SUCCESS:
                if error_override:
                    error_code = error_override
                else:
                    error_code = self._select_error_code()
                error_message = self._get_error_message(error_code)
            
            # Create transaction
            txn = Transaction(
                amount=round(random.uniform(100, 50000), 2),
                payment_method=payment_method,
                issuer_bank=issuer_bank,
                acquiring_bank=random.choice(["HDFC", "ICICI", "AXIS"]),
                gateway=gateway,
                route_id=f"{issuer_bank}_{payment_method.value}_{gateway}",
                status=status,
                error_code=error_code,
                error_message=error_message,
                latency_ms=round(latency, 2),
                processing_cost=round(random.uniform(0.5, 3.0), 2),
                merchant_id=merchant,
                customer_id=f"CUST_{random.randint(10000, 99999)}",
                region=region
            )
            
            # Maybe add to retry queue
            if status != TransactionStatus.SUCCESS and random.random() < 0.4:
                self.pending_retries.append((txn, 1))
            
            return txn
    
    def _generate_retry(self, original: Transaction, attempt: int) -> Transaction:
        """Generate a retry transaction."""
        # Retries often have better success (fresh connection)
        success_prob = min(0.95, 0.85 + attempt * 0.03)
        
        # Apply chaos to retries too
        success_mod, latency_mod, error_override = self._apply_chaos(
            original.issuer_bank,
            original.payment_method,
            original.gateway,
            original.region
        )
        success_prob *= success_mod
        
        is_success = random.random() < success_prob
        status = TransactionStatus.SUCCESS if is_success else TransactionStatus.FAILURE
        
        base_latency = self.config.base_latency.get(
            original.payment_method.value, (1000, 300)
        )
        latency = max(50, np.random.normal(
            base_latency[0] * latency_mod,
            base_latency[1] * latency_mod
        ))
        
        error_code = None
        error_message = None
        if status != TransactionStatus.SUCCESS:
            error_code = error_override or self._select_error_code()
            error_message = self._get_error_message(error_code)
            
            # Maybe retry again (up to 3 attempts)
            if attempt < 3 and random.random() < 0.3:
                self.pending_retries.append((original, attempt + 1))
        
        return Transaction(
            amount=original.amount,
            payment_method=original.payment_method,
            issuer_bank=original.issuer_bank,
            acquiring_bank=original.acquiring_bank,
            gateway=original.gateway,
            route_id=original.route_id,
            status=status,
            error_code=error_code,
            error_message=error_message,
            latency_ms=round(latency, 2),
            processing_cost=round(original.processing_cost * 1.1, 2),  # Retries cost more
            is_retry=True,
            retry_count=attempt,
            original_txn_id=original.id,
            merchant_id=original.merchant_id,
            customer_id=original.customer_id,
            region=original.region
        )
    
    def _apply_chaos(
        self,
        bank: str,
        method: PaymentMethod,
        gateway: str,
        region: str
    ) -> Tuple[float, float, Optional[str]]:
        """Apply active chaos scenarios and return modifiers."""
        success_mod = 1.0
        latency_mod = 1.0
        error_override = None
        
        # Clean up expired scenarios
        self.active_scenarios = [s for s in self.active_scenarios if s.is_active]
        
        for scenario in self.active_scenarios:
            if random.random() > scenario.impact_probability:
                continue
                
            applies = False
            if scenario.entity_type == "bank" and scenario.affected_entity == bank:
                applies = True
            elif scenario.entity_type == "method" and scenario.affected_entity == method.value:
                applies = True
            elif scenario.entity_type == "gateway" and scenario.affected_entity == gateway:
                applies = True
            elif scenario.entity_type == "region" and scenario.affected_entity == region:
                applies = True
            elif scenario.affected_entity == "all":
                applies = True
            
            if applies:
                success_mod *= scenario.success_rate_modifier
                latency_mod *= scenario.latency_modifier
                if scenario.error_code_override:
                    error_override = scenario.error_code_override
        
        return success_mod, latency_mod, error_override
    
    def _select_error_code(self) -> str:
        """Select an error code based on configured distribution."""
        codes = list(self.config.error_codes.keys())
        weights = list(self.config.error_codes.values())
        return random.choices(codes, weights=weights, k=1)[0]
    
    def _get_error_message(self, code: str) -> str:
        """Get human-readable message for error code."""
        messages = {
            "E001_INSUFFICIENT_FUNDS": "Transaction declined due to insufficient funds",
            "E002_CARD_EXPIRED": "The card has expired",
            "E003_INVALID_CVV": "Invalid CVV provided",
            "E004_BANK_DECLINED": "Transaction declined by issuing bank",
            "E005_NETWORK_ERROR": "Network connectivity error",
            "E006_TIMEOUT": "Transaction timed out",
            "E007_ISSUER_UNAVAILABLE": "Issuer bank temporarily unavailable",
            "E008_FRAUD_SUSPECTED": "Transaction flagged for potential fraud",
            "E009_LIMIT_EXCEEDED": "Transaction limit exceeded",
            "E010_INVALID_OTP": "Invalid or expired OTP",
            "E011_SESSION_EXPIRED": "Payment session expired",
            "E012_DUPLICATE_TXN": "Duplicate transaction detected",
            "E013_BANK_THROTTLING": "Bank is throttling requests",
            "E014_GATEWAY_ERROR": "Payment gateway error",
            "E015_3DS_FAILURE": "3D Secure authentication failed"
        }
        return messages.get(code, "Unknown error")
    
    # ==========================================================================
    # CHAOS SCENARIO CREATORS
    # ==========================================================================
    
    def _create_issuer_degradation(self, bank: str = None, duration: int = 300) -> ChaosScenario:
        """Create an issuer degradation scenario."""
        target_bank = bank or random.choice(self.config.banks)
        return ChaosScenario(
            name=f"issuer_degradation_{target_bank}",
            description=f"{target_bank} bank experiencing service degradation",
            affected_entity=target_bank,
            entity_type="bank",
            success_rate_modifier=random.uniform(0.3, 0.6),
            latency_modifier=random.uniform(1.5, 3.0),
            error_code_override="E007_ISSUER_UNAVAILABLE",
            duration_seconds=duration,
            impact_probability=0.85
        )
    
    def _create_retry_storm(self, duration: int = 120) -> ChaosScenario:
        """Create a retry storm scenario (system-wide)."""
        # Flood the pending retries
        for _ in range(20):
            fake_txn = Transaction(
                payment_method=random.choice(list(PaymentMethod)),
                issuer_bank=random.choice(self.config.banks),
                gateway=random.choice(self.gateways),
                status=TransactionStatus.FAILURE
            )
            self.pending_retries.append((fake_txn, 1))
        
        return ChaosScenario(
            name="retry_storm",
            description="High volume of retry attempts overwhelming the system",
            affected_entity="all",
            entity_type="all",
            success_rate_modifier=0.7,
            latency_modifier=1.8,
            duration_seconds=duration,
            impact_probability=0.6
        )
    
    def _create_method_fatigue(self, method: str = None, duration: int = 600) -> ChaosScenario:
        """Create a payment method fatigue scenario."""
        target_method = method or random.choice([m.value for m in PaymentMethod])
        return ChaosScenario(
            name=f"method_fatigue_{target_method}",
            description=f"{target_method.upper()} payment method showing degraded performance",
            affected_entity=target_method,
            entity_type="method",
            success_rate_modifier=random.uniform(0.6, 0.8),
            latency_modifier=1.3,
            duration_seconds=duration,
            impact_probability=0.75
        )
    
    def _create_latency_spike(self, gateway: str = None, duration: int = 180) -> ChaosScenario:
        """Create a latency spike on a gateway."""
        target_gateway = gateway or random.choice(self.gateways)
        return ChaosScenario(
            name=f"latency_spike_{target_gateway}",
            description=f"{target_gateway} experiencing high latency",
            affected_entity=target_gateway,
            entity_type="gateway",
            success_rate_modifier=0.95,  # Success rate mostly OK
            latency_modifier=random.uniform(2.5, 5.0),
            duration_seconds=duration,
            impact_probability=0.9
        )
    
    def _create_gateway_issues(self, gateway: str = None, duration: int = 240) -> ChaosScenario:
        """Create gateway reliability issues."""
        target_gateway = gateway or random.choice(self.gateways)
        return ChaosScenario(
            name=f"gateway_issues_{target_gateway}",
            description=f"{target_gateway} experiencing reliability issues",
            affected_entity=target_gateway,
            entity_type="gateway",
            success_rate_modifier=random.uniform(0.4, 0.7),
            latency_modifier=random.uniform(1.5, 2.5),
            error_code_override="E014_GATEWAY_ERROR",
            duration_seconds=duration,
            impact_probability=0.8
        )
    
    def _create_peak_hour_load(self, duration: int = 900) -> ChaosScenario:
        """Create peak hour load scenario."""
        return ChaosScenario(
            name="peak_hour_load",
            description="High traffic volume causing system strain",
            affected_entity="all",
            entity_type="all",
            success_rate_modifier=0.85,
            latency_modifier=1.5,
            duration_seconds=duration,
            impact_probability=0.5
        )
    
    def inject_chaos(self, scenario_type: str, **kwargs) -> Optional[ChaosScenario]:
        """Inject a chaos scenario into the simulation."""
        creator = self.chaos_templates.get(scenario_type)
        if creator:
            scenario = creator(**kwargs)
            self.active_scenarios.append(scenario)
            return scenario
        return None
    
    def inject_random_chaos(self) -> Optional[ChaosScenario]:
        """Randomly inject a chaos scenario."""
        if random.random() < self.config.chaos_probability:
            scenario_type = random.choice(list(self.chaos_templates.keys()))
            return self.inject_chaos(scenario_type)
        return None
    
    def clear_chaos(self):
        """Clear all active chaos scenarios."""
        self.active_scenarios = []
        self.pending_retries = []
    
    def get_active_scenarios(self) -> List[Dict]:
        """Get list of active scenarios with details."""
        return [
            {
                "name": s.name,
                "description": s.description,
                "affected_entity": s.affected_entity,
                "remaining_seconds": s.remaining_seconds,
                "success_rate_modifier": s.success_rate_modifier,
                "latency_modifier": s.latency_modifier
            }
            for s in self.active_scenarios if s.is_active
        ]
    
    def generate_batch(self, count: int) -> List[Transaction]:
        """Generate a batch of transactions."""
        return [self.generate_transaction() for _ in range(count)]
    
    def get_stats(self) -> Dict:
        """Get simulator statistics."""
        return {
            "total_transactions": self.transaction_counter,
            "active_scenarios": len([s for s in self.active_scenarios if s.is_active]),
            "pending_retries": len(self.pending_retries),
            "chaos_probability": self.config.chaos_probability
        }
