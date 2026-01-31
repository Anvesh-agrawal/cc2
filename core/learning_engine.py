"""
Learning Engine
===============
Outcome tracking, hypothesis validation, and adaptive strategy updates.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from collections import defaultdict
from dataclasses import dataclass, field
import statistics

from config import LearningConfig, PatternType, ActionType, config
from models.hypothesis import ActionOutcome, Hypothesis, ActionRecommendation, Pattern


@dataclass
class StrategyState:
    """Current state of an adaptive strategy."""
    name: str
    parameters: Dict[str, Any]
    performance_score: float = 0.0
    updates_count: int = 0
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class LearningEvent:
    """A learning event recording what was learned."""
    timestamp: datetime = field(default_factory=datetime.now)
    event_type: str = ""  # "outcome_positive", "outcome_negative", "hypothesis_validated", etc.
    source_action_id: Optional[str] = None
    source_hypothesis_id: Optional[str] = None
    learning: str = ""
    impact: Dict[str, Any] = field(default_factory=dict)


class LearningEngine:
    """
    Implements the learning loop for the payment agent system.
    
    Features:
    - Outcome tracking and evaluation
    - Hypothesis validation
    - Adaptive strategy updates
    - Performance feedback to other components
    """
    
    def __init__(self, config: LearningConfig = None):
        self.config = config or LearningConfig()
        
        # Outcome history
        self.outcomes: Dict[str, ActionOutcome] = {}
        self.outcome_history: List[ActionOutcome] = []
        
        # Hypothesis tracking
        self.validated_hypotheses: Dict[str, Tuple[Hypothesis, bool]] = {}  # id -> (hypothesis, was_correct)
        
        # Strategy states
        self.strategies: Dict[str, StrategyState] = self._initialize_strategies()
        
        # Learning events
        self.events: List[LearningEvent] = []
        
        # Performance metrics
        self.action_type_performance: Dict[str, Dict] = defaultdict(
            lambda: {"total": 0, "successful": 0, "avg_improvement": 0.0}
        )
        
        # Pattern-action effectiveness
        self.pattern_action_effectiveness: Dict[Tuple[str, str], Dict] = defaultdict(
            lambda: {"attempts": 0, "successes": 0, "avg_delta": 0.0}
        )
        
        # Callbacks for strategy updates
        self.on_strategy_updated: Optional[callable] = None
        self.on_learning_event: Optional[callable] = None
    
    def _initialize_strategies(self) -> Dict[str, StrategyState]:
        """Initialize default strategies."""
        return {
            "retry_timing": StrategyState(
                name="retry_timing",
                parameters={
                    "base_delay_ms": 1000,
                    "max_delay_ms": 8000,
                    "backoff_factor": 2.0,
                    "max_retries": 3
                }
            ),
            "traffic_routing": StrategyState(
                name="traffic_routing",
                parameters={
                    "exploration_rate": 0.1,
                    "success_weight": 0.5,
                    "latency_weight": 0.3,
                    "cost_weight": 0.2
                }
            ),
            "pattern_sensitivity": StrategyState(
                name="pattern_sensitivity",
                parameters={
                    "issuer_degradation_threshold": 2.0,
                    "retry_storm_threshold": 0.3,
                    "latency_spike_threshold": 2.5
                }
            ),
            "intervention_aggression": StrategyState(
                name="intervention_aggression",
                parameters={
                    "min_confidence_to_act": 0.6,
                    "max_traffic_shift": 0.2,
                    "cooldown_seconds": 60
                }
            )
        }
    
    def record_outcome(
        self,
        action: ActionRecommendation,
        pre_metrics: Dict[str, float],
        post_metrics: Dict[str, float],
        sample_size: int = 0
    ) -> ActionOutcome:
        """Record the outcome of an executed action."""
        outcome = ActionOutcome(
            action_id=action.id,
            action_type=action.action_type,
            pre_success_rate=pre_metrics.get("success_rate", 0),
            pre_avg_latency=pre_metrics.get("avg_latency", 0),
            pre_error_rate=pre_metrics.get("error_rate", 0),
            post_success_rate=post_metrics.get("success_rate", 0),
            post_avg_latency=post_metrics.get("avg_latency", 0),
            post_error_rate=post_metrics.get("error_rate", 0),
            sample_size=sample_size
        )
        
        # Evaluate the outcome
        outcome.evaluate()
        
        # Store outcome
        self.outcomes[action.id] = outcome
        self.outcome_history.append(outcome)
        
        # Update action type performance
        self._update_action_performance(outcome)
        
        # Generate learnings
        learnings = self._generate_learnings(action, outcome)
        outcome.learnings = learnings
        
        # Update strategies based on outcome
        strategy_updates = self._update_strategies(action, outcome)
        outcome.strategy_updates = strategy_updates
        
        # Create learning event
        event = LearningEvent(
            event_type="outcome_positive" if outcome.was_successful else "outcome_negative",
            source_action_id=action.id,
            learning="; ".join(learnings),
            impact=strategy_updates
        )
        self.events.append(event)
        
        if self.on_learning_event:
            self.on_learning_event(event)
        
        return outcome
    
    def _update_action_performance(self, outcome: ActionOutcome):
        """Update performance tracking for action types."""
        action_type = outcome.action_type.value
        perf = self.action_type_performance[action_type]
        
        perf["total"] += 1
        if outcome.was_successful:
            perf["successful"] += 1
        
        # Update rolling average improvement
        old_avg = perf["avg_improvement"]
        perf["avg_improvement"] = (
            old_avg * (perf["total"] - 1) + outcome.success_rate_delta
        ) / perf["total"]
    
    def _generate_learnings(
        self,
        action: ActionRecommendation,
        outcome: ActionOutcome
    ) -> List[str]:
        """Generate human-readable learnings from an outcome."""
        learnings = []
        
        if outcome.was_successful:
            learnings.append(
                f"{action.action_type.value} action improved success rate by "
                f"{outcome.success_rate_delta:.1%}"
            )
            
            if outcome.latency_delta < 0:
                learnings.append(
                    f"Latency also improved by {-outcome.latency_delta:.0f}ms"
                )
        else:
            if outcome.success_rate_delta < 0:
                learnings.append(
                    f"{action.action_type.value} action decreased success rate by "
                    f"{-outcome.success_rate_delta:.1%}"
                )
            
            if outcome.latency_delta > 0:
                learnings.append(
                    f"Latency increased by {outcome.latency_delta:.0f}ms"
                )
            
            learnings.append("Consider reducing aggressiveness for similar situations")
        
        return learnings
    
    def _update_strategies(
        self,
        action: ActionRecommendation,
        outcome: ActionOutcome
    ) -> Dict[str, Any]:
        """Update strategies based on outcome."""
        updates = {}
        
        # Update intervention aggression based on outcome
        if action.action_type in [ActionType.REROUTE_TRAFFIC, ActionType.SUPPRESS_PATH]:
            strategy = self.strategies["intervention_aggression"]
            
            if outcome.was_successful:
                # Action worked, we can be slightly more aggressive
                new_max_shift = min(
                    0.3,
                    strategy.parameters["max_traffic_shift"] * (1 + self.config.adaptation_rate)
                )
                if new_max_shift != strategy.parameters["max_traffic_shift"]:
                    updates["max_traffic_shift"] = {
                        "old": strategy.parameters["max_traffic_shift"],
                        "new": new_max_shift
                    }
                    strategy.parameters["max_traffic_shift"] = new_max_shift
            else:
                # Action failed, be more conservative
                new_max_shift = max(
                    0.05,
                    strategy.parameters["max_traffic_shift"] * (1 - self.config.adaptation_rate)
                )
                if new_max_shift != strategy.parameters["max_traffic_shift"]:
                    updates["max_traffic_shift"] = {
                        "old": strategy.parameters["max_traffic_shift"],
                        "new": new_max_shift
                    }
                    strategy.parameters["max_traffic_shift"] = new_max_shift
            
            strategy.updates_count += 1
            strategy.last_updated = datetime.now()
        
        # Update retry timing if relevant
        if action.action_type == ActionType.ADJUST_RETRY_STRATEGY:
            strategy = self.strategies["retry_timing"]
            
            if outcome.was_successful:
                # Current settings work well
                strategy.performance_score = min(
                    1.0,
                    strategy.performance_score + 0.1
                )
            else:
                # Maybe adjust timing
                strategy.performance_score = max(
                    0.0,
                    strategy.performance_score - 0.1
                )
                
                # If performance is low, try increasing delays
                if strategy.performance_score < 0.3:
                    old_delay = strategy.parameters["base_delay_ms"]
                    new_delay = min(2000, old_delay + 250)
                    if new_delay != old_delay:
                        updates["base_delay_ms"] = {"old": old_delay, "new": new_delay}
                        strategy.parameters["base_delay_ms"] = new_delay
            
            strategy.updates_count += 1
            strategy.last_updated = datetime.now()
        
        # Update routing strategy weights
        if action.action_type == ActionType.REROUTE_TRAFFIC:
            strategy = self.strategies["traffic_routing"]
            
            # Adjust exploration rate based on outcome
            if outcome.was_successful:
                # Successful routes found, can reduce exploration
                new_rate = max(
                    0.05,
                    strategy.parameters["exploration_rate"] * 0.95
                )
            else:
                # Need more exploration
                new_rate = min(
                    0.2,
                    strategy.parameters["exploration_rate"] * 1.1
                )
            
            if new_rate != strategy.parameters["exploration_rate"]:
                updates["exploration_rate"] = {
                    "old": strategy.parameters["exploration_rate"],
                    "new": new_rate
                }
                strategy.parameters["exploration_rate"] = new_rate
            
            strategy.updates_count += 1
            strategy.last_updated = datetime.now()
        
        if updates and self.on_strategy_updated:
            self.on_strategy_updated(updates)
        
        return updates
    
    def validate_hypothesis(
        self,
        hypothesis: Hypothesis,
        observed_outcome: Optional[ActionOutcome] = None,
        pattern_resolved: bool = False
    ) -> bool:
        """
        Validate a hypothesis based on observed outcomes.
        
        Returns True if hypothesis was validated as correct.
        """
        was_correct = False
        
        if pattern_resolved:
            # If the pattern was resolved after acting on hypothesis, it was likely correct
            was_correct = True
            hypothesis.is_validated = True
            hypothesis.validation_result = True
            hypothesis.validated_at = datetime.now()
        elif observed_outcome:
            # Check if the action based on hypothesis helped
            if observed_outcome.was_successful:
                was_correct = True
                hypothesis.is_validated = True
                hypothesis.validation_result = True
                hypothesis.validated_at = datetime.now()
            elif observed_outcome.was_rolled_back:
                was_correct = False
                hypothesis.is_validated = True
                hypothesis.validation_result = False
                hypothesis.validated_at = datetime.now()
        
        # Store validation result
        self.validated_hypotheses[hypothesis.id] = (hypothesis, was_correct)
        
        # Update pattern sensitivity if hypothesis was wrong
        if hypothesis.is_validated and not was_correct:
            self._adjust_pattern_sensitivity(hypothesis.pattern_type, decrease=True)
        elif hypothesis.is_validated and was_correct:
            self._adjust_pattern_sensitivity(hypothesis.pattern_type, decrease=False)
        
        # Create learning event
        event = LearningEvent(
            event_type="hypothesis_validated" if was_correct else "hypothesis_invalidated",
            source_hypothesis_id=hypothesis.id,
            learning=f"Hypothesis about {hypothesis.pattern_type.value} was {'correct' if was_correct else 'incorrect'}",
            impact={"pattern_type": hypothesis.pattern_type.value, "was_correct": was_correct}
        )
        self.events.append(event)
        
        return was_correct
    
    def _adjust_pattern_sensitivity(self, pattern_type: PatternType, decrease: bool):
        """Adjust pattern detection sensitivity based on hypothesis validation."""
        strategy = self.strategies["pattern_sensitivity"]
        
        param_map = {
            PatternType.ISSUER_DEGRADATION: "issuer_degradation_threshold",
            PatternType.RETRY_STORM: "retry_storm_threshold",
            PatternType.LATENCY_SPIKE: "latency_spike_threshold"
        }
        
        param_name = param_map.get(pattern_type)
        if not param_name:
            return
        
        current = strategy.parameters[param_name]
        
        if decrease:
            # Hypothesis was wrong, be less sensitive (higher threshold for z-scores)
            # For retry storm, higher threshold means more retries needed to trigger
            new_value = current * (1 + self.config.adaptation_rate)
        else:
            # Hypothesis was right, can be slightly more sensitive
            new_value = current * (1 - self.config.adaptation_rate * 0.5)
        
        strategy.parameters[param_name] = new_value
        strategy.updates_count += 1
        strategy.last_updated = datetime.now()
    
    def track_pattern_action_effectiveness(
        self,
        pattern_type: PatternType,
        action_type: ActionType,
        was_effective: bool,
        improvement_delta: float
    ):
        """Track how effective specific action types are for specific patterns."""
        key = (pattern_type.value, action_type.value)
        perf = self.pattern_action_effectiveness[key]
        
        perf["attempts"] += 1
        if was_effective:
            perf["successes"] += 1
        
        # Update rolling average delta
        old_avg = perf["avg_delta"]
        perf["avg_delta"] = (
            old_avg * (perf["attempts"] - 1) + improvement_delta
        ) / perf["attempts"]
    
    def get_recommended_action_for_pattern(
        self,
        pattern_type: PatternType
    ) -> Optional[ActionType]:
        """Get the most effective action type for a given pattern based on history."""
        best_action = None
        best_score = 0.0
        
        for (pt, at), perf in self.pattern_action_effectiveness.items():
            if pt == pattern_type.value and perf["attempts"] >= 3:
                success_rate = perf["successes"] / perf["attempts"]
                score = success_rate * (1 + perf["avg_delta"])
                
                if score > best_score:
                    best_score = score
                    best_action = ActionType(at)
        
        return best_action
    
    def get_strategy(self, name: str) -> Optional[StrategyState]:
        """Get current state of a strategy."""
        return self.strategies.get(name)
    
    def get_all_strategies(self) -> Dict[str, Dict]:
        """Get all strategy states."""
        return {
            name: {
                "parameters": state.parameters,
                "performance_score": state.performance_score,
                "updates_count": state.updates_count,
                "last_updated": state.last_updated
            }
            for name, state in self.strategies.items()
        }
    
    def get_action_type_stats(self) -> Dict[str, Dict]:
        """Get performance statistics by action type."""
        return {
            action_type: {
                "total": perf["total"],
                "successful": perf["successful"],
                "success_rate": perf["successful"] / max(1, perf["total"]),
                "avg_improvement": perf["avg_improvement"]
            }
            for action_type, perf in self.action_type_performance.items()
        }
    
    def get_recent_learnings(self, limit: int = 10) -> List[Dict]:
        """Get recent learning events."""
        recent = sorted(self.events, key=lambda e: e.timestamp, reverse=True)[:limit]
        return [
            {
                "timestamp": e.timestamp,
                "event_type": e.event_type,
                "learning": e.learning,
                "impact": e.impact
            }
            for e in recent
        ]
    
    def get_hypothesis_accuracy(self) -> Dict:
        """Get statistics on hypothesis accuracy."""
        if not self.validated_hypotheses:
            return {"total": 0, "correct": 0, "accuracy": 0.0}
        
        correct = sum(1 for _, was_correct in self.validated_hypotheses.values() if was_correct)
        total = len(self.validated_hypotheses)
        
        return {
            "total": total,
            "correct": correct,
            "accuracy": correct / total
        }
    
    def get_stats(self) -> Dict:
        """Get learning engine statistics."""
        return {
            "total_outcomes": len(self.outcome_history),
            "successful_outcomes": sum(1 for o in self.outcome_history if o.was_successful),
            "hypothesis_accuracy": self.get_hypothesis_accuracy(),
            "strategy_updates": sum(s.updates_count for s in self.strategies.values()),
            "learning_events": len(self.events)
        }
