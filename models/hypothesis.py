"""
Hypothesis Models
=================
Data classes for patterns, hypotheses, and action recommendations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
import uuid

from config import PatternType, ActionType, AutonomyLevel, AgentRole


@dataclass
class Pattern:
    """A detected pattern in payment data."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    detected_at: datetime = field(default_factory=datetime.now)
    
    # Pattern classification
    pattern_type: PatternType = PatternType.ISSUER_DEGRADATION
    severity: float = 0.0  # 0-1 scale
    
    # Context
    affected_entity: str = ""  # Bank name, method, region, etc.
    affected_transactions: int = 0
    
    # Statistical evidence
    baseline_value: float = 0.0
    current_value: float = 0.0
    z_score: float = 0.0
    confidence: float = 0.0  # 0-1 scale
    
    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_significant(self) -> bool:
        return self.confidence >= 0.6
    
    @property
    def severity_label(self) -> str:
        if self.severity >= 0.8:
            return "CRITICAL"
        elif self.severity >= 0.6:
            return "HIGH"
        elif self.severity >= 0.4:
            return "MEDIUM"
        else:
            return "LOW"
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "detected_at": self.detected_at,
            "pattern_type": self.pattern_type.value,
            "severity": self.severity,
            "severity_label": self.severity_label,
            "affected_entity": self.affected_entity,
            "affected_transactions": self.affected_transactions,
            "baseline_value": self.baseline_value,
            "current_value": self.current_value,
            "z_score": self.z_score,
            "confidence": self.confidence,
            "metadata": self.metadata
        }
    
    def describe(self) -> str:
        """Human-readable description of the pattern."""
        descriptions = {
            PatternType.ISSUER_DEGRADATION: f"Issuer {self.affected_entity} showing degraded performance: success rate dropped from {self.baseline_value:.1%} to {self.current_value:.1%}",
            PatternType.RETRY_STORM: f"Retry storm detected: {self.current_value:.1%} of transactions are retries (threshold: {self.baseline_value:.1%})",
            PatternType.METHOD_FATIGUE: f"Payment method {self.affected_entity} showing fatigue: success rate dropped by {(self.baseline_value - self.current_value):.1%}",
            PatternType.LATENCY_SPIKE: f"Latency spike on {self.affected_entity}: P95 increased from {self.baseline_value:.0f}ms to {self.current_value:.0f}ms",
            PatternType.ERROR_CLUSTERING: f"Error clustering detected: {self.affected_entity} represents {self.current_value:.1%} of all errors",
            PatternType.GEOGRAPHIC_ANOMALY: f"Geographic anomaly in {self.affected_entity}: failure rate {self.current_value:.1%}",
            PatternType.PEAK_HOUR_FAILURE: f"Peak hour failure pattern: success rate {self.current_value:.1%} vs baseline {self.baseline_value:.1%}"
        }
        return descriptions.get(self.pattern_type, f"Unknown pattern on {self.affected_entity}")


@dataclass
class Hypothesis:
    """A hypothesis about the root cause of a pattern."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: datetime = field(default_factory=datetime.now)
    
    # Link to pattern
    pattern_id: str = ""
    pattern_type: PatternType = PatternType.ISSUER_DEGRADATION
    
    # Hypothesis details
    description: str = ""
    root_cause: str = ""
    confidence: float = 0.0  # 0-1 scale
    
    # Evidence
    supporting_evidence: List[str] = field(default_factory=list)
    contradicting_evidence: List[str] = field(default_factory=list)
    
    # State
    is_validated: bool = False
    validation_result: Optional[bool] = None
    validated_at: Optional[datetime] = None
    
    # Expiry
    expires_at: datetime = None
    
    def __post_init__(self):
        if self.expires_at is None:
            from datetime import timedelta
            self.expires_at = self.created_at + timedelta(minutes=10)
    
    @property
    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at
    
    @property
    def is_actionable(self) -> bool:
        return self.confidence >= 0.6 and not self.is_expired
    
    def add_evidence(self, evidence: str, supporting: bool = True):
        """Add evidence to the hypothesis."""
        if supporting:
            self.supporting_evidence.append(evidence)
        else:
            self.contradicting_evidence.append(evidence)
        self._update_confidence()
    
    def _update_confidence(self):
        """Update confidence based on evidence balance."""
        supporting = len(self.supporting_evidence)
        contradicting = len(self.contradicting_evidence)
        total = supporting + contradicting
        if total > 0:
            self.confidence = min(0.95, (supporting / total) * (1 - 0.5 ** total))
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type.value,
            "description": self.description,
            "root_cause": self.root_cause,
            "confidence": self.confidence,
            "supporting_evidence": self.supporting_evidence,
            "contradicting_evidence": self.contradicting_evidence,
            "is_validated": self.is_validated,
            "is_actionable": self.is_actionable,
            "is_expired": self.is_expired
        }


@dataclass
class ActionRecommendation:
    """A recommended action to address a pattern/hypothesis."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: datetime = field(default_factory=datetime.now)
    
    # Link to hypothesis
    hypothesis_id: str = ""
    pattern_id: str = ""
    
    # Action details
    action_type: ActionType = ActionType.ALERT_OPS
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Autonomy
    autonomy_level: AutonomyLevel = AutonomyLevel.MANUAL
    requires_approval: bool = True
    
    # Impact estimation
    expected_success_rate_delta: float = 0.0
    expected_latency_delta: float = 0.0
    expected_cost_delta: float = 0.0
    risk_score: float = 0.0  # 0-1 scale
    
    # Agent attribution
    proposed_by: AgentRole = AgentRole.OPTIMIZER
    approved_by: Optional[AgentRole] = None
    
    # State
    is_approved: bool = False
    is_executed: bool = False
    execution_time: Optional[datetime] = None
    
    # Rollback info
    can_rollback: bool = True
    rollback_params: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def net_benefit_score(self) -> float:
        """Calculate net benefit score considering all factors."""
        success_benefit = self.expected_success_rate_delta * 100  # Weight success heavily
        latency_benefit = -self.expected_latency_delta / 100      # Lower latency is better
        cost_penalty = -self.expected_cost_delta * 10             # Cost penalty
        risk_penalty = -self.risk_score * 20                      # Risk penalty
        return success_benefit + latency_benefit + cost_penalty + risk_penalty
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "hypothesis_id": self.hypothesis_id,
            "action_type": self.action_type.value,
            "description": self.description,
            "parameters": self.parameters,
            "autonomy_level": self.autonomy_level.value,
            "requires_approval": self.requires_approval,
            "expected_success_rate_delta": self.expected_success_rate_delta,
            "expected_latency_delta": self.expected_latency_delta,
            "risk_score": self.risk_score,
            "net_benefit_score": self.net_benefit_score,
            "proposed_by": self.proposed_by.value,
            "is_approved": self.is_approved,
            "is_executed": self.is_executed
        }
    
    def describe(self) -> str:
        """Human-readable description of the action."""
        return f"[{self.action_type.value.upper()}] {self.description}"


@dataclass
class ActionOutcome:
    """The outcome of an executed action."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    recorded_at: datetime = field(default_factory=datetime.now)
    
    # Link to action
    action_id: str = ""
    action_type: ActionType = ActionType.ALERT_OPS
    
    # Pre-action metrics
    pre_success_rate: float = 0.0
    pre_avg_latency: float = 0.0
    pre_error_rate: float = 0.0
    
    # Post-action metrics
    post_success_rate: float = 0.0
    post_avg_latency: float = 0.0
    post_error_rate: float = 0.0
    
    # Evaluation
    measurement_window_seconds: int = 60
    sample_size: int = 0
    
    # Results
    success_rate_delta: float = 0.0
    latency_delta: float = 0.0
    
    # Verdict
    was_successful: bool = False
    was_rolled_back: bool = False
    rollback_reason: Optional[str] = None
    
    # Learnings
    learnings: List[str] = field(default_factory=list)
    strategy_updates: Dict[str, Any] = field(default_factory=dict)
    
    def evaluate(self):
        """Evaluate the outcome based on pre/post metrics."""
        self.success_rate_delta = self.post_success_rate - self.pre_success_rate
        self.latency_delta = self.post_avg_latency - self.pre_avg_latency
        
        # Action is successful if success rate improved or stayed same without latency increase
        self.was_successful = (
            self.success_rate_delta >= 0 and 
            self.latency_delta <= self.pre_avg_latency * 0.1  # Max 10% latency increase
        )
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "recorded_at": self.recorded_at,
            "action_id": self.action_id,
            "action_type": self.action_type.value,
            "pre_success_rate": self.pre_success_rate,
            "post_success_rate": self.post_success_rate,
            "success_rate_delta": self.success_rate_delta,
            "pre_avg_latency": self.pre_avg_latency,
            "post_avg_latency": self.post_avg_latency,
            "latency_delta": self.latency_delta,
            "was_successful": self.was_successful,
            "was_rolled_back": self.was_rolled_back,
            "learnings": self.learnings
        }


@dataclass  
class NegotiationRecord:
    """Record of negotiation between agents."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Participants
    initiator: AgentRole = AgentRole.OPTIMIZER
    respondent: AgentRole = AgentRole.RISK_OFFICER
    
    # Original proposal
    original_action: ActionRecommendation = None
    
    # Negotiation rounds
    rounds: List[Dict[str, Any]] = field(default_factory=list)
    
    # Final outcome
    final_action: Optional[ActionRecommendation] = None
    consensus_reached: bool = False
    final_decision: str = ""  # "approved", "modified", "rejected"
    
    # Reasoning
    optimizer_reasoning: str = ""
    risk_officer_reasoning: str = ""
    compromise_details: str = ""
    
    def add_round(self, proposer: AgentRole, proposal: Dict, response: str):
        """Add a negotiation round."""
        self.rounds.append({
            "proposer": proposer.value,
            "proposal": proposal,
            "response": response,
            "timestamp": datetime.now()
        })
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "initiator": self.initiator.value,
            "respondent": self.respondent.value,
            "original_action_type": self.original_action.action_type.value if self.original_action else None,
            "rounds_count": len(self.rounds),
            "consensus_reached": self.consensus_reached,
            "final_decision": self.final_decision,
            "optimizer_reasoning": self.optimizer_reasoning,
            "risk_officer_reasoning": self.risk_officer_reasoning,
            "compromise_details": self.compromise_details
        }
