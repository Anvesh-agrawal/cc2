"""
Optimizer Agent
===============
Agent focused on maximizing payment success rate and minimizing latency.
"""

from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from config import (
    PatternType, ActionType, AutonomyLevel, AgentRole,
    OptimizerConfig, config
)
from models.hypothesis import Pattern, Hypothesis, ActionRecommendation
from models.transaction import TransactionBatch


@dataclass
class OptimizationGoal:
    """An optimization goal with target and current value."""
    name: str
    target: float
    current: float
    weight: float
    direction: str = "maximize"  # "maximize" or "minimize"
    
    @property
    def gap(self) -> float:
        if self.direction == "maximize":
            return max(0, self.target - self.current)
        else:
            return max(0, self.current - self.target)
    
    @property
    def score(self) -> float:
        if self.direction == "maximize":
            return min(1.0, self.current / self.target) if self.target > 0 else 0
        else:
            return min(1.0, self.target / self.current) if self.current > 0 else 1


class OptimizerAgent:
    """
    Optimizer Agent - Focuses on improving payment performance.
    
    Responsibilities:
    - Analyze patterns and hypotheses
    - Propose optimization actions
    - Balance success rate, latency, and cost
    - Willing to take calculated risks for improvement
    """
    
    def __init__(self, config: OptimizerConfig = None):
        self.config = config or OptimizerConfig()
        self.role = AgentRole.OPTIMIZER
        
        # Optimization goals
        self.goals = [
            OptimizationGoal("success_rate", target=0.95, current=0.90, weight=self.config.success_weight),
            OptimizationGoal("latency_p95", target=2000, current=2500, weight=self.config.latency_weight, direction="minimize"),
            OptimizationGoal("processing_cost", target=1.5, current=2.0, weight=self.config.cost_weight, direction="minimize")
        ]
        
        # Recent decisions
        self.decision_history: List[Dict] = []
        
        # Learned preferences
        self.pattern_action_preferences: Dict[str, ActionType] = {
            PatternType.ISSUER_DEGRADATION.value: ActionType.REROUTE_TRAFFIC,
            PatternType.RETRY_STORM.value: ActionType.ADJUST_RETRY_STRATEGY,
            PatternType.METHOD_FATIGUE.value: ActionType.RECOMMEND_METHOD,
            PatternType.LATENCY_SPIKE.value: ActionType.REROUTE_TRAFFIC,
            PatternType.ERROR_CLUSTERING.value: ActionType.ALERT_OPS,
        }
    
    def analyze_situation(
        self,
        patterns: List[Pattern],
        hypotheses: List[Hypothesis],
        current_metrics: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Analyze the current situation and identify optimization opportunities.
        
        Returns:
            Analysis including urgency, opportunities, and recommended focus areas.
        """
        # Update current goal values
        self.goals[0].current = current_metrics.get("success_rate", 0.9)
        self.goals[1].current = current_metrics.get("latency_p95", 2500)
        self.goals[2].current = current_metrics.get("avg_cost", 2.0)
        
        # Calculate overall health score
        health_score = sum(g.score * g.weight for g in self.goals)
        
        # Identify most pressing issues
        pressing_issues = []
        for pattern in patterns:
            if pattern.severity >= 0.6:
                pressing_issues.append({
                    "type": pattern.pattern_type.value,
                    "entity": pattern.affected_entity,
                    "severity": pattern.severity,
                    "description": pattern.describe()
                })
        
        # Sort by severity
        pressing_issues.sort(key=lambda x: x["severity"], reverse=True)
        
        # Identify actionable hypotheses
        actionable_hypotheses = [
            {
                "id": h.id,
                "pattern_type": h.pattern_type.value,
                "description": h.description,
                "confidence": h.confidence,
                "root_cause": h.root_cause
            }
            for h in hypotheses if h.is_actionable
        ]
        
        # Determine urgency level
        if any(p.severity >= 0.8 for p in patterns):
            urgency = "CRITICAL"
        elif any(p.severity >= 0.6 for p in patterns):
            urgency = "HIGH"
        elif any(p.severity >= 0.4 for p in patterns):
            urgency = "MEDIUM"
        else:
            urgency = "LOW"
        
        return {
            "health_score": round(health_score, 3),
            "urgency": urgency,
            "pressing_issues": pressing_issues[:5],
            "actionable_hypotheses": actionable_hypotheses,
            "goal_gaps": [
                {"goal": g.name, "gap": round(g.gap, 4), "score": round(g.score, 3)}
                for g in self.goals
            ],
            "recommendation": self._generate_recommendation(patterns, hypotheses)
        }
    
    def _generate_recommendation(
        self,
        patterns: List[Pattern],
        hypotheses: List[Hypothesis]
    ) -> str:
        """Generate a high-level recommendation."""
        if not patterns:
            return "System healthy. Continue monitoring."
        
        most_severe = max(patterns, key=lambda p: p.severity)
        
        if most_severe.severity >= 0.8:
            return f"URGENT: Address {most_severe.pattern_type.value} on {most_severe.affected_entity}"
        elif most_severe.severity >= 0.5:
            return f"ATTENTION: {most_severe.pattern_type.value} detected. Consider intervention."
        else:
            return "Minor patterns detected. Monitoring recommended."
    
    def propose_action(
        self,
        pattern: Pattern,
        hypothesis: Hypothesis,
        current_metrics: Dict[str, float],
        route_options: List[Dict] = None
    ) -> Optional[ActionRecommendation]:
        """
        Propose an action to address a pattern/hypothesis.
        
        Returns:
            ActionRecommendation if action is warranted, None otherwise.
        """
        # Determine best action type for this pattern
        action_type = self.pattern_action_preferences.get(
            pattern.pattern_type.value,
            ActionType.ALERT_OPS
        )
        
        # Build action parameters based on type
        params = {}
        description = ""
        expected_improvement = 0.0
        risk_score = 0.0
        
        if action_type == ActionType.REROUTE_TRAFFIC:
            # Calculate how much traffic to shift
            severity_factor = min(1.0, pattern.severity + 0.2)
            traffic_pct = min(
                self.config.max_traffic_shift_autonomous * 100,
                severity_factor * 30  # Up to 30% for critical
            )
            
            # Find best alternative route
            best_alternative = None
            if route_options:
                available = [r for r in route_options if r.get("route_id") != pattern.affected_entity]
                if available:
                    best_alternative = max(available, key=lambda r: r.get("success_rate", 0))
            
            params = {
                "from_entity": pattern.affected_entity,
                "to_entity": best_alternative.get("route_id") if best_alternative else "auto_select",
                "traffic_percentage": traffic_pct,
                "duration_seconds": 300
            }
            description = (
                f"Route {traffic_pct:.0f}% of traffic away from {pattern.affected_entity} "
                f"to {params['to_entity']}"
            )
            expected_improvement = pattern.baseline_value - pattern.current_value  # Recover the drop
            risk_score = traffic_pct / 100 * 0.5  # Higher traffic shift = higher risk
        
        elif action_type == ActionType.ADJUST_RETRY_STRATEGY:
            # Modify retry timing
            current_delay = self.config.preferred_retry_delays[0]
            new_delay = current_delay * 1.5 if pattern.severity > 0.5 else current_delay * 1.2
            
            params = {
                "base_delay_ms": new_delay,
                "max_retries": 2 if pattern.severity > 0.7 else 3,
                "backoff_factor": 2.5 if pattern.pattern_type == PatternType.RETRY_STORM else 2.0
            }
            description = (
                f"Adjust retry strategy: delay={new_delay:.0f}ms, "
                f"max_retries={params['max_retries']}"
            )
            expected_improvement = 0.03  # Modest improvement expected
            risk_score = 0.2
        
        elif action_type == ActionType.RECOMMEND_METHOD:
            # Recommend alternative payment method
            if pattern.pattern_type == PatternType.METHOD_FATIGUE:
                fatigued_method = pattern.affected_entity
                alternatives = ["card", "upi", "wallet", "netbanking"]
                recommended = next((m for m in alternatives if m != fatigued_method), fatigued_method)
                
                params = {
                    "fatigued_method": fatigued_method,
                    "recommended_method": recommended,
                    "show_recommendation": True
                }
                description = f"Recommend {recommended.upper()} as alternative to {fatigued_method.upper()}"
                expected_improvement = 0.02
                risk_score = 0.1
        
        elif action_type == ActionType.SUPPRESS_PATH:
            # Temporarily suppress a failing path
            params = {
                "path": pattern.affected_entity,
                "duration_seconds": 180,
                "reason": hypothesis.root_cause
            }
            description = f"Temporarily suppress {pattern.affected_entity} for 3 minutes"
            expected_improvement = 0.05
            risk_score = 0.4
        
        elif action_type == ActionType.CIRCUIT_BREAK:
            # Emergency circuit breaker
            params = {
                "entity": pattern.affected_entity,
                "entity_type": "bank" if pattern.pattern_type == PatternType.ISSUER_DEGRADATION else "gateway",
                "threshold": 0.5,
                "cooldown_seconds": 300
            }
            description = f"Activate circuit breaker on {pattern.affected_entity}"
            expected_improvement = 0.08
            risk_score = 0.5
        
        else:  # ALERT_OPS
            params = {
                "severity": pattern.severity_label,
                "pattern": pattern.pattern_type.value,
                "entity": pattern.affected_entity,
                "message": hypothesis.description
            }
            description = f"Alert ops team about {pattern.pattern_type.value}"
            expected_improvement = 0.0
            risk_score = 0.0
        
        # Determine autonomy level
        if risk_score <= 0.2:
            autonomy = AutonomyLevel.AUTONOMOUS
            requires_approval = False
        elif risk_score <= 0.4:
            autonomy = AutonomyLevel.SEMI_AUTONOMOUS
            requires_approval = True
        else:
            autonomy = AutonomyLevel.MANUAL
            requires_approval = True
        
        # Create recommendation
        recommendation = ActionRecommendation(
            hypothesis_id=hypothesis.id,
            pattern_id=pattern.id,
            action_type=action_type,
            description=description,
            parameters=params,
            autonomy_level=autonomy,
            requires_approval=requires_approval,
            expected_success_rate_delta=expected_improvement,
            expected_latency_delta=-100 if action_type == ActionType.REROUTE_TRAFFIC else 0,
            risk_score=risk_score,
            proposed_by=self.role,
            can_rollback=action_type in [
                ActionType.REROUTE_TRAFFIC,
                ActionType.ADJUST_RETRY_STRATEGY,
                ActionType.SUPPRESS_PATH
            ],
            rollback_params={"original_state": current_metrics}
        )
        
        # Record decision
        self.decision_history.append({
            "timestamp": datetime.now(),
            "pattern_id": pattern.id,
            "action_type": action_type.value,
            "risk_score": risk_score,
            "expected_improvement": expected_improvement
        })
        
        return recommendation
    
    def get_reasoning(self, action: ActionRecommendation) -> str:
        """Generate human-readable reasoning for an action."""
        reasoning_parts = [
            f"I'm proposing a {action.action_type.value} action because:",
            f"",
            f"1. **Pattern detected**: {action.description}",
            f"2. **Expected improvement**: {action.expected_success_rate_delta:.1%} in success rate",
            f"3. **Risk assessment**: {action.risk_score:.1%} risk score",
            f"4. **Confidence**: Based on hypothesis with ID {action.hypothesis_id}",
            f"",
            f"Trade-offs considered:",
            f"- Success rate weight: {self.config.success_weight}",
            f"- Latency weight: {self.config.latency_weight}",
            f"- Cost weight: {self.config.cost_weight}",
            f"",
            f"This action {'can' if action.can_rollback else 'cannot'} be rolled back if needed."
        ]
        return "\n".join(reasoning_parts)
    
    def update_preferences(self, pattern_type: str, action_type: ActionType, was_successful: bool):
        """Update action preferences based on outcome."""
        if was_successful:
            self.pattern_action_preferences[pattern_type] = action_type
    
    def get_stats(self) -> Dict:
        """Get agent statistics."""
        return {
            "role": self.role.value,
            "decisions_made": len(self.decision_history),
            "current_goals": [
                {"name": g.name, "target": g.target, "current": g.current, "score": g.score}
                for g in self.goals
            ],
            "pattern_preferences": {k: v.value for k, v in self.pattern_action_preferences.items()}
        }
