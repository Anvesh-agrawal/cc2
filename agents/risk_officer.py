"""
Risk Officer Agent
==================
Agent focused on safety, compliance, and preventing catastrophic failures.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import deque

from config import (
    PatternType, ActionType, AutonomyLevel, AgentRole,
    RiskOfficerConfig, config
)
from models.hypothesis import ActionRecommendation


@dataclass
class RiskAssessment:
    """Assessment of risk for a proposed action."""
    action_id: str
    overall_risk: float  # 0-1 scale
    risk_factors: List[Dict[str, Any]]
    mitigations: List[str]
    verdict: str  # "approve", "modify", "reject"
    conditions: List[str] = field(default_factory=list)
    reasoning: str = ""


@dataclass
class SafetyConstraint:
    """A safety constraint that must be satisfied."""
    name: str
    description: str
    check_function: str  # Name of the check method
    severity: str = "hard"  # "hard" (block) or "soft" (warn)
    is_active: bool = True


class RiskOfficerAgent:
    """
    Risk Officer Agent - Ensures safety and compliance.
    
    Responsibilities:
    - Evaluate risk of proposed actions
    - Enforce safety constraints
    - Veto dangerous actions
    - Ensure rollback capabilities exist
    - Monitor for compliance violations
    """
    
    def __init__(self, config: RiskOfficerConfig = None):
        self.config = config or RiskOfficerConfig()
        self.role = AgentRole.RISK_OFFICER
        
        # Veto history
        self.veto_history: List[Dict] = []
        
        # Approval history
        self.approval_history: List[Dict] = []
        
        # Recent action rate tracking
        self.recent_actions: deque = deque(maxlen=50)
        
        # Safety constraints
        self.constraints = self._initialize_constraints()
        
        # Risk thresholds by action type
        self.action_risk_thresholds = {
            ActionType.ALERT_OPS: 1.0,  # Always OK
            ActionType.RECOMMEND_METHOD: 0.8,
            ActionType.ADJUST_RETRY_STRATEGY: 0.7,
            ActionType.REROUTE_TRAFFIC: 0.5,
            ActionType.SUPPRESS_PATH: 0.4,
            ActionType.CIRCUIT_BREAK: 0.3
        }
        
        # Incident tracking
        self.active_incidents: List[Dict] = []
    
    def _initialize_constraints(self) -> List[SafetyConstraint]:
        """Initialize safety constraints."""
        return [
            SafetyConstraint(
                name="max_retry_count",
                description=f"Retries must not exceed {self.config.max_retry_count}",
                check_function="check_retry_limit"
            ),
            SafetyConstraint(
                name="max_cost",
                description=f"Cost per transaction must not exceed {self.config.max_cost_per_txn}",
                check_function="check_cost_limit"
            ),
            SafetyConstraint(
                name="fraud_threshold",
                description=f"Fraud score must be below {self.config.fraud_score_threshold}",
                check_function="check_fraud_score"
            ),
            SafetyConstraint(
                name="rate_limit",
                description=f"Max {self.config.max_actions_per_window} actions per {self.config.action_window_seconds}s",
                check_function="check_rate_limit"
            ),
            SafetyConstraint(
                name="traffic_shift_limit",
                description=f"Traffic shifts must not exceed {self.config.traffic_shift_veto_threshold * 100}%",
                check_function="check_traffic_shift"
            ),
            SafetyConstraint(
                name="rollback_required",
                description="High-risk actions must have rollback capability",
                check_function="check_rollback_capability",
                severity="soft"
            )
        ]
    
    def assess_risk(
        self,
        action: ActionRecommendation,
        current_metrics: Dict[str, float] = None
    ) -> RiskAssessment:
        """
        Assess the risk of a proposed action.
        
        Returns:
            RiskAssessment with verdict and conditions.
        """
        risk_factors = []
        mitigations = []
        conditions = []
        
        # Base risk from the action itself
        base_risk = action.risk_score
        risk_factors.append({
            "factor": "base_action_risk",
            "value": base_risk,
            "description": f"Inherent risk of {action.action_type.value}"
        })
        
        # Check each constraint
        constraint_violations = []
        for constraint in self.constraints:
            if not constraint.is_active:
                continue
                
            is_violated, details = self._check_constraint(constraint, action)
            if is_violated:
                constraint_violations.append({
                    "constraint": constraint.name,
                    "severity": constraint.severity,
                    "details": details
                })
                
                if constraint.severity == "hard":
                    risk_factors.append({
                        "factor": f"constraint_violation_{constraint.name}",
                        "value": 1.0,
                        "description": details
                    })
        
        # Check action-specific risks
        specific_risks = self._assess_action_specific_risks(action)
        risk_factors.extend(specific_risks)
        
        # Calculate overall risk
        overall_risk = self._calculate_overall_risk(risk_factors)
        
        # Determine verdict
        risk_threshold = self.action_risk_thresholds.get(action.action_type, 0.5)
        has_hard_violations = any(
            v["severity"] == "hard" for v in constraint_violations
        )
        
        if has_hard_violations:
            verdict = "reject"
            reasoning = self._generate_rejection_reasoning(constraint_violations)
        elif overall_risk > risk_threshold:
            # Can we modify to reduce risk?
            can_modify, modifications = self._can_modify_to_reduce_risk(action)
            if can_modify:
                verdict = "modify"
                conditions = modifications
                mitigations.append("Action can be modified to reduce risk")
                reasoning = self._generate_modification_reasoning(action, modifications)
            else:
                verdict = "reject"
                reasoning = f"Risk {overall_risk:.2f} exceeds threshold {risk_threshold:.2f}"
        else:
            verdict = "approve"
            reasoning = self._generate_approval_reasoning(action, overall_risk, risk_threshold)
            
            # Add monitoring conditions for approved actions
            conditions.append(f"Monitor for {self.config.post_action_monitoring_seconds}s after execution")
            conditions.append(f"Auto-rollback if success rate drops > {self.config.success_rate_drop_trigger * 100:.0f}%")
        
        # Add mitigations
        if action.can_rollback:
            mitigations.append("Rollback capability available")
        if overall_risk <= 0.3:
            mitigations.append("Low inherent risk")
        
        assessment = RiskAssessment(
            action_id=action.id,
            overall_risk=overall_risk,
            risk_factors=risk_factors,
            mitigations=mitigations,
            verdict=verdict,
            conditions=conditions,
            reasoning=reasoning
        )
        
        # Record assessment
        if verdict == "reject":
            self.veto_history.append({
                "timestamp": datetime.now(),
                "action_id": action.id,
                "action_type": action.action_type.value,
                "risk": overall_risk,
                "reason": reasoning
            })
        else:
            self.approval_history.append({
                "timestamp": datetime.now(),
                "action_id": action.id,
                "action_type": action.action_type.value,
                "risk": overall_risk,
                "verdict": verdict,
                "conditions": conditions
            })
        
        return assessment
    
    def _check_constraint(
        self,
        constraint: SafetyConstraint,
        action: ActionRecommendation
    ) -> Tuple[bool, str]:
        """Check if an action violates a constraint."""
        
        if constraint.check_function == "check_retry_limit":
            max_retries = action.parameters.get("max_retries", 3)
            if max_retries > self.config.max_retry_count:
                return True, f"Max retries {max_retries} exceeds limit {self.config.max_retry_count}"
            return False, ""
        
        elif constraint.check_function == "check_cost_limit":
            # For cost-increasing actions
            cost_delta = action.expected_cost_delta if hasattr(action, 'expected_cost_delta') else 0
            if cost_delta > self.config.max_cost_per_txn:
                return True, f"Cost increase {cost_delta} exceeds limit"
            return False, ""
        
        elif constraint.check_function == "check_fraud_score":
            # Would need actual fraud context
            return False, ""
        
        elif constraint.check_function == "check_rate_limit":
            now = datetime.now()
            window_start = now - timedelta(seconds=self.config.action_window_seconds)
            recent = sum(1 for a in self.recent_actions if a.get("timestamp", now) > window_start)
            if recent >= self.config.max_actions_per_window:
                return True, f"Rate limit: {recent} actions in window (max {self.config.max_actions_per_window})"
            return False, ""
        
        elif constraint.check_function == "check_traffic_shift":
            if action.action_type == ActionType.REROUTE_TRAFFIC:
                traffic_pct = action.parameters.get("traffic_percentage", 0) / 100
                if traffic_pct > self.config.traffic_shift_veto_threshold:
                    return True, f"Traffic shift {traffic_pct * 100:.0f}% exceeds limit {self.config.traffic_shift_veto_threshold * 100:.0f}%"
            return False, ""
        
        elif constraint.check_function == "check_rollback_capability":
            if action.risk_score > 0.5 and not action.can_rollback:
                return True, "High-risk action without rollback capability"
            return False, ""
        
        return False, ""
    
    def _assess_action_specific_risks(self, action: ActionRecommendation) -> List[Dict]:
        """Assess risks specific to the action type."""
        risks = []
        
        if action.action_type == ActionType.REROUTE_TRAFFIC:
            traffic_pct = action.parameters.get("traffic_percentage", 0)
            if traffic_pct > 10:
                risks.append({
                    "factor": "significant_traffic_shift",
                    "value": traffic_pct / 100,
                    "description": f"Shifting {traffic_pct}% of traffic is significant"
                })
            
            # Check if rerouting to unknown destination
            if action.parameters.get("to_entity") == "auto_select":
                risks.append({
                    "factor": "unknown_destination",
                    "value": 0.2,
                    "description": "Destination route not explicitly specified"
                })
        
        elif action.action_type == ActionType.SUPPRESS_PATH:
            duration = action.parameters.get("duration_seconds", 0)
            if duration > 300:
                risks.append({
                    "factor": "long_suppression",
                    "value": min(1.0, duration / 600),
                    "description": f"Suppressing for {duration}s is long"
                })
        
        elif action.action_type == ActionType.CIRCUIT_BREAK:
            risks.append({
                "factor": "circuit_breaker_active",
                "value": 0.3,
                "description": "Circuit breakers can cause traffic loss"
            })
        
        return risks
    
    def _calculate_overall_risk(self, risk_factors: List[Dict]) -> float:
        """Calculate overall risk from factors."""
        if not risk_factors:
            return 0.0
        
        # Use max risk with weighted average as blend
        max_risk = max(f["value"] for f in risk_factors)
        avg_risk = sum(f["value"] for f in risk_factors) / len(risk_factors)
        
        # Blend: 60% max, 40% average
        return 0.6 * max_risk + 0.4 * avg_risk
    
    def _can_modify_to_reduce_risk(
        self,
        action: ActionRecommendation
    ) -> Tuple[bool, List[str]]:
        """Check if we can suggest modifications to reduce risk."""
        modifications = []
        
        if action.action_type == ActionType.REROUTE_TRAFFIC:
            traffic_pct = action.parameters.get("traffic_percentage", 0)
            max_allowed = self.config.traffic_shift_veto_threshold * 100
            if traffic_pct > max_allowed:
                modifications.append(f"Reduce traffic shift to {max_allowed:.0f}%")
            modifications.append("Add gradual ramp-up over 5 minutes")
        
        elif action.action_type == ActionType.SUPPRESS_PATH:
            duration = action.parameters.get("duration_seconds", 0)
            if duration > 300:
                modifications.append("Reduce suppression duration to 180s")
            modifications.append("Add health check before extending suppression")
        
        elif action.action_type == ActionType.ADJUST_RETRY_STRATEGY:
            max_retries = action.parameters.get("max_retries", 3)
            if max_retries > 2:
                modifications.append("Limit retries to 2 maximum")
        
        return len(modifications) > 0, modifications
    
    def _generate_rejection_reasoning(self, violations: List[Dict]) -> str:
        """Generate reasoning for rejection."""
        parts = ["I cannot approve this action because:"]
        for v in violations:
            if v["severity"] == "hard":
                parts.append(f"- **VIOLATION**: {v['details']}")
            else:
                parts.append(f"- Warning: {v['details']}")
        return "\n".join(parts)
    
    def _generate_modification_reasoning(
        self,
        action: ActionRecommendation,
        modifications: List[str]
    ) -> str:
        """Generate reasoning for modification request."""
        parts = [
            f"I can approve {action.action_type.value} with modifications:",
            ""
        ]
        for m in modifications:
            parts.append(f"- {m}")
        parts.append("")
        parts.append("This reduces overall risk while preserving the intended benefit.")
        return "\n".join(parts)
    
    def _generate_approval_reasoning(
        self,
        action: ActionRecommendation,
        risk: float,
        threshold: float
    ) -> str:
        """Generate reasoning for approval."""
        return (
            f"Approving {action.action_type.value} action.\n"
            f"Risk assessment: {risk:.2f} (threshold: {threshold:.2f})\n"
            f"Expected benefit: {action.expected_success_rate_delta:.1%} success rate improvement\n"
            f"Rollback available: {'Yes' if action.can_rollback else 'No'}"
        )
    
    def veto(self, action: ActionRecommendation, reason: str) -> Dict:
        """Explicitly veto an action."""
        veto_record = {
            "timestamp": datetime.now(),
            "action_id": action.id,
            "action_type": action.action_type.value,
            "reason": reason,
            "type": "explicit_veto"
        }
        self.veto_history.append(veto_record)
        return veto_record
    
    def record_action(self, action: ActionRecommendation):
        """Record that an action was taken (for rate limiting)."""
        self.recent_actions.append({
            "timestamp": datetime.now(),
            "action_id": action.id,
            "action_type": action.action_type.value
        })
    
    def raise_incident(self, severity: str, description: str, affected_entity: str):
        """Raise a safety incident."""
        incident = {
            "id": f"INC_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "timestamp": datetime.now(),
            "severity": severity,
            "description": description,
            "affected_entity": affected_entity,
            "status": "open"
        }
        self.active_incidents.append(incident)
        return incident
    
    def resolve_incident(self, incident_id: str, resolution: str):
        """Resolve an incident."""
        for incident in self.active_incidents:
            if incident["id"] == incident_id:
                incident["status"] = "resolved"
                incident["resolution"] = resolution
                incident["resolved_at"] = datetime.now()
                return True
        return False
    
    def get_active_incidents(self) -> List[Dict]:
        """Get list of active incidents."""
        return [i for i in self.active_incidents if i["status"] == "open"]
    
    def get_stats(self) -> Dict:
        """Get agent statistics."""
        now = datetime.now()
        window_start = now - timedelta(seconds=self.config.action_window_seconds)
        recent_actions = sum(1 for a in self.recent_actions if a.get("timestamp", now) > window_start)
        
        return {
            "role": self.role.value,
            "total_vetoes": len(self.veto_history),
            "total_approvals": len(self.approval_history),
            "veto_rate": len(self.veto_history) / max(1, len(self.veto_history) + len(self.approval_history)),
            "actions_in_window": recent_actions,
            "window_limit": self.config.max_actions_per_window,
            "active_incidents": len(self.get_active_incidents()),
            "active_constraints": sum(1 for c in self.constraints if c.is_active)
        }
    
    def get_reasoning(self, assessment: RiskAssessment) -> str:
        """Generate detailed reasoning for a risk assessment using LLM."""
        # Try LLM-enhanced reasoning first
        try:
            from core.llm_client import get_gemini_client
            client = get_gemini_client()
            if client:
                context = {
                    "action_id": assessment.action_id,
                    "verdict": assessment.verdict,
                    "overall_risk": assessment.overall_risk,
                    "risk_factors": [f"{f['factor']}: {f['description']}" for f in assessment.risk_factors],
                    "mitigations": assessment.mitigations,
                    "conditions": assessment.conditions,
                }
                llm_reasoning = client.generate_reasoning(context, "risk_officer")
                if llm_reasoning:
                    # Prepend with structured header
                    header = (
                        f"## Risk Assessment for Action {assessment.action_id}\n\n"
                        f"**Verdict**: {assessment.verdict.upper()}\n"
                        f"**Overall Risk**: {assessment.overall_risk:.2%}\n\n"
                    )
                    return header + llm_reasoning
        except Exception as e:
            print(f"[RiskOfficerAgent] LLM reasoning failed: {e}")
        
        # Fallback to template-based reasoning
        return self._template_reasoning(assessment)
    
    def _template_reasoning(self, assessment: RiskAssessment) -> str:
        """Generate template-based reasoning (fallback)."""
        parts = [
            f"## Risk Assessment for Action {assessment.action_id}",
            "",
            f"**Verdict**: {assessment.verdict.upper()}",
            f"**Overall Risk**: {assessment.overall_risk:.2%}",
            "",
            "### Risk Factors:",
        ]
        
        for factor in assessment.risk_factors:
            parts.append(f"- {factor['factor']}: {factor['value']:.2f} - {factor['description']}")
        
        if assessment.mitigations:
            parts.append("")
            parts.append("### Mitigations:")
            for m in assessment.mitigations:
                parts.append(f"- {m}")
        
        if assessment.conditions:
            parts.append("")
            parts.append("### Conditions:")
            for c in assessment.conditions:
                parts.append(f"- {c}")
        
        parts.append("")
        parts.append("### Reasoning:")
        parts.append(assessment.reasoning)
        
        return "\n".join(parts)
