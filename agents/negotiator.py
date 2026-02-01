"""
Negotiation Engine
==================
Facilitates negotiation between Optimizer and Risk Officer agents.
"""

from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass, field

from config import ActionType, AgentRole
from models.hypothesis import ActionRecommendation, NegotiationRecord
from agents.optimizer import OptimizerAgent
from agents.risk_officer import RiskOfficerAgent, RiskAssessment


@dataclass
class NegotiationResult:
    """Result of a negotiation between agents."""
    success: bool
    final_action: Optional[ActionRecommendation]
    decision: str  # "approved", "modified", "rejected"
    rounds: int
    optimizer_reasoning: str
    risk_officer_reasoning: str
    compromise_details: str = ""


class NegotiationEngine:
    """
    Negotiation Engine - Facilitates consensus between agents.
    
    Responsibilities:
    - Mediate between Optimizer and Risk Officer
    - Find acceptable compromises
    - Document negotiation process
    - Ensure decisions are explainable
    """
    
    def __init__(
        self,
        optimizer: OptimizerAgent,
        risk_officer: RiskOfficerAgent,
        max_rounds: int = 3
    ):
        self.optimizer = optimizer
        self.risk_officer = risk_officer
        self.max_rounds = max_rounds
        
        # Negotiation history
        self.negotiation_history: List[NegotiationRecord] = []
        
        # Compromise strategies
        self.compromise_strategies = {
            ActionType.REROUTE_TRAFFIC: self._compromise_reroute,
            ActionType.SUPPRESS_PATH: self._compromise_suppress,
            ActionType.ADJUST_RETRY_STRATEGY: self._compromise_retry,
            ActionType.CIRCUIT_BREAK: self._compromise_circuit_break,
        }
    
    def negotiate(
        self,
        proposed_action: ActionRecommendation,
        current_metrics: Dict[str, float] = None
    ) -> NegotiationResult:
        """
        Negotiate an action between Optimizer and Risk Officer.
        
        Returns:
            NegotiationResult with final decision and reasoning.
        """
        record = NegotiationRecord(
            initiator=AgentRole.OPTIMIZER,
            respondent=AgentRole.RISK_OFFICER,
            original_action=proposed_action
        )
        
        current_action = proposed_action
        rounds = 0
        last_assessment = None
        
        # Negotiation loop
        while rounds < self.max_rounds:
            rounds += 1
            
            # Risk Officer assesses the current proposal
            assessment = self.risk_officer.assess_risk(current_action, current_metrics)
            last_assessment = assessment
            
            # Record the round
            record.add_round(
                proposer=AgentRole.OPTIMIZER if rounds == 1 else AgentRole.RISK_OFFICER,
                proposal=current_action.to_dict(),
                response=assessment.verdict
            )
            
            if assessment.verdict == "approve":
                # Consensus reached!
                record.consensus_reached = True
                record.final_action = current_action
                record.final_decision = "approved"
                record.optimizer_reasoning = self.optimizer.get_reasoning(current_action)
                record.risk_officer_reasoning = self.risk_officer.get_reasoning(assessment)
                break
            
            elif assessment.verdict == "modify" and rounds < self.max_rounds:
                # Try to find a compromise
                modified_action = self._apply_compromise(
                    current_action,
                    assessment
                )
                
                if modified_action:
                    current_action = modified_action
                    record.compromise_details = f"Modified in round {rounds}: {', '.join(assessment.conditions)}"
                else:
                    # Can't modify, cycle to rejection
                    break
            
            else:
                # Rejected
                break
        
        # Final result
        if record.consensus_reached:
            result = NegotiationResult(
                success=True,
                final_action=record.final_action,
                decision="approved",
                rounds=rounds,
                optimizer_reasoning=record.optimizer_reasoning,
                risk_officer_reasoning=record.risk_officer_reasoning,
                compromise_details=record.compromise_details
            )
        elif last_assessment and last_assessment.verdict == "modify":
            # Ended on modify - apply final modifications and approve with conditions
            final_action = self._apply_compromise(current_action, last_assessment)
            if final_action:
                record.consensus_reached = True
                record.final_action = final_action
                record.final_decision = "modified"
                
                result = NegotiationResult(
                    success=True,
                    final_action=final_action,
                    decision="modified",
                    rounds=rounds,
                    optimizer_reasoning=self.optimizer.get_reasoning(final_action),
                    risk_officer_reasoning=self.risk_officer.get_reasoning(last_assessment),
                    compromise_details=record.compromise_details
                )
            else:
                result = NegotiationResult(
                    success=False,
                    final_action=None,
                    decision="rejected",
                    rounds=rounds,
                    optimizer_reasoning=self.optimizer.get_reasoning(proposed_action),
                    risk_officer_reasoning=self.risk_officer.get_reasoning(last_assessment) if last_assessment else "No assessment",
                    compromise_details="Could not find acceptable compromise"
                )
        else:
            record.final_decision = "rejected"
            record.optimizer_reasoning = self.optimizer.get_reasoning(proposed_action)
            record.risk_officer_reasoning = self.risk_officer.get_reasoning(last_assessment) if last_assessment else "No assessment"
            
            result = NegotiationResult(
                success=False,
                final_action=None,
                decision="rejected",
                rounds=rounds,
                optimizer_reasoning=record.optimizer_reasoning,
                risk_officer_reasoning=record.risk_officer_reasoning
            )
        
        # Store negotiation record
        self.negotiation_history.append(record)
        
        return result
    
    def _apply_compromise(
        self,
        action: ActionRecommendation,
        assessment: RiskAssessment
    ) -> Optional[ActionRecommendation]:
        """Apply compromise strategies to modify an action."""
        strategy = self.compromise_strategies.get(action.action_type)
        
        if strategy:
            return strategy(action, assessment)
        
        # Default: reduce risk score and mark as requiring approval
        modified = ActionRecommendation(
            hypothesis_id=action.hypothesis_id,
            pattern_id=action.pattern_id,
            action_type=action.action_type,
            description=action.description + " (modified)",
            parameters=action.parameters.copy(),
            autonomy_level=action.autonomy_level,
            requires_approval=True,  # Force approval
            expected_success_rate_delta=action.expected_success_rate_delta * 0.8,
            expected_latency_delta=action.expected_latency_delta,
            risk_score=action.risk_score * 0.8,
            proposed_by=action.proposed_by,
            can_rollback=action.can_rollback,
            rollback_params=action.rollback_params
        )
        return modified
    
    def _compromise_reroute(
        self,
        action: ActionRecommendation,
        assessment: RiskAssessment
    ) -> ActionRecommendation:
        """Compromise strategy for traffic rerouting."""
        new_params = action.parameters.copy()
        
        # Reduce traffic percentage
        current_pct = new_params.get("traffic_percentage", 20)
        new_pct = min(current_pct, 10)  # Cap at 10%
        new_params["traffic_percentage"] = new_pct
        
        # Add gradual ramp-up
        new_params["ramp_up_minutes"] = 5
        
        # Reduce duration
        new_params["duration_seconds"] = min(
            new_params.get("duration_seconds", 300),
            180
        )
        
        return ActionRecommendation(
            hypothesis_id=action.hypothesis_id,
            pattern_id=action.pattern_id,
            action_type=action.action_type,
            description=f"Route {new_pct:.0f}% of traffic (reduced from {current_pct:.0f}%) with gradual ramp-up",
            parameters=new_params,
            autonomy_level=action.autonomy_level,
            requires_approval=action.requires_approval,
            expected_success_rate_delta=action.expected_success_rate_delta * (new_pct / current_pct),
            expected_latency_delta=action.expected_latency_delta,
            risk_score=action.risk_score * 0.6,
            proposed_by=action.proposed_by,
            can_rollback=True,
            rollback_params=action.rollback_params
        )
    
    def _compromise_suppress(
        self,
        action: ActionRecommendation,
        assessment: RiskAssessment
    ) -> ActionRecommendation:
        """Compromise strategy for path suppression."""
        new_params = action.parameters.copy()
        
        # Reduce suppression duration
        new_params["duration_seconds"] = min(
            new_params.get("duration_seconds", 180),
            120  # Max 2 minutes
        )
        
        # Add auto health check
        new_params["health_check_interval"] = 30
        
        return ActionRecommendation(
            hypothesis_id=action.hypothesis_id,
            pattern_id=action.pattern_id,
            action_type=action.action_type,
            description=f"Suppress path for {new_params['duration_seconds']}s with health checks",
            parameters=new_params,
            autonomy_level=action.autonomy_level,
            requires_approval=action.requires_approval,
            expected_success_rate_delta=action.expected_success_rate_delta * 0.8,
            expected_latency_delta=action.expected_latency_delta,
            risk_score=action.risk_score * 0.7,
            proposed_by=action.proposed_by,
            can_rollback=True,
            rollback_params=action.rollback_params
        )
    
    def _compromise_retry(
        self,
        action: ActionRecommendation,
        assessment: RiskAssessment
    ) -> ActionRecommendation:
        """Compromise strategy for retry adjustment."""
        new_params = action.parameters.copy()
        
        # Limit retries
        new_params["max_retries"] = min(new_params.get("max_retries", 3), 2)
        
        # Increase delay to reduce load
        new_params["base_delay_ms"] = max(new_params.get("base_delay_ms", 1000), 1500)
        
        return ActionRecommendation(
            hypothesis_id=action.hypothesis_id,
            pattern_id=action.pattern_id,
            action_type=action.action_type,
            description=f"Retry strategy: max {new_params['max_retries']} retries, {new_params['base_delay_ms']}ms delay",
            parameters=new_params,
            autonomy_level=action.autonomy_level,
            requires_approval=False,  # Retry changes are usually safe
            expected_success_rate_delta=action.expected_success_rate_delta,
            expected_latency_delta=action.expected_latency_delta,
            risk_score=action.risk_score * 0.5,
            proposed_by=action.proposed_by,
            can_rollback=True,
            rollback_params=action.rollback_params
        )
    
    def _compromise_circuit_break(
        self,
        action: ActionRecommendation,
        assessment: RiskAssessment
    ) -> ActionRecommendation:
        """Compromise strategy for circuit breaker."""
        new_params = action.parameters.copy()
        
        # Increase threshold (less aggressive)
        new_params["threshold"] = min(new_params.get("threshold", 0.5), 0.4)
        
        # Shorter cooldown
        new_params["cooldown_seconds"] = min(new_params.get("cooldown_seconds", 300), 180)
        
        # Add gradual recovery
        new_params["gradual_recovery"] = True
        new_params["recovery_steps"] = 3
        
        return ActionRecommendation(
            hypothesis_id=action.hypothesis_id,
            pattern_id=action.pattern_id,
            action_type=action.action_type,
            description=f"Circuit breaker with gradual recovery, {new_params['cooldown_seconds']}s cooldown",
            parameters=new_params,
            autonomy_level=action.autonomy_level,
            requires_approval=True,  # Circuit breakers always need approval
            expected_success_rate_delta=action.expected_success_rate_delta,
            expected_latency_delta=action.expected_latency_delta,
            risk_score=action.risk_score * 0.7,
            proposed_by=action.proposed_by,
            can_rollback=True,
            rollback_params=action.rollback_params
        )
    
    def get_negotiation_summary(self, record: NegotiationRecord) -> str:
        """Generate a summary of a negotiation using LLM."""
        # Try LLM-enhanced summary first
        try:
            from core.llm_client import get_gemini_client
            client = get_gemini_client()
            if client:
                context = {
                    "decision": record.final_decision or "pending",
                    "rounds": len(record.rounds),
                    "optimizer_reasoning": record.optimizer_reasoning or "Not available",
                    "risk_officer_reasoning": record.risk_officer_reasoning or "Not available",
                    "compromise_details": record.compromise_details or "None",
                }
                llm_summary = client.generate_reasoning(context, "negotiator")
                if llm_summary:
                    # Prepend with structured header
                    action_type = record.original_action.action_type.value if record.original_action else "N/A"
                    consensus = "Reached" if record.consensus_reached else "Not reached"
                    header = (
                        f"## Negotiation Summary\n\n"
                        f"**Original Action**: {action_type}\n"
                        f"**Rounds**: {len(record.rounds)}\n"
                        f"**Consensus**: {consensus}\n"
                        f"**Final Decision**: {(record.final_decision or 'pending').upper()}\n\n"
                    )
                    return header + llm_summary
        except Exception as e:
            print(f"[NegotiationEngine] LLM summary failed: {e}")
        
        # Fallback to template-based summary
        return self._template_summary(record)
    
    def _template_summary(self, record: NegotiationRecord) -> str:
        """Generate template-based negotiation summary (fallback)."""
        lines = [
            f"## Negotiation Summary",
            f"",
            f"**Original Action**: {record.original_action.action_type.value if record.original_action else 'N/A'}",
            f"**Rounds**: {len(record.rounds)}",
            f"**Consensus**: {'Reached' if record.consensus_reached else 'Not reached'}",
            f"**Final Decision**: {(record.final_decision or 'pending').upper()}",
            f"",
            f"### Negotiation Rounds:",
        ]
        
        for i, round in enumerate(record.rounds, 1):
            lines.append(f"- **Round {i}**: {round['proposer']} proposed → {round['response']}")
        
        if record.compromise_details:
            lines.append(f"")
            lines.append(f"### Compromise Details:")
            lines.append(record.compromise_details)
        
        lines.append(f"")
        lines.append(f"### Optimizer Reasoning:")
        lines.append(record.optimizer_reasoning or "Not available")
        
        lines.append(f"")
        lines.append(f"### Risk Officer Reasoning:")
        lines.append(record.risk_officer_reasoning or "Not available")
        
        return "\n".join(lines)
    
    def get_recent_negotiations(self, limit: int = 10) -> List[Dict]:
        """Get recent negotiation summaries."""
        recent = sorted(
            self.negotiation_history,
            key=lambda r: r.timestamp,
            reverse=True
        )[:limit]
        
        return [r.to_dict() for r in recent]
    
    def get_stats(self) -> Dict:
        """Get negotiation statistics."""
        total = len(self.negotiation_history)
        if total == 0:
            return {
                "total_negotiations": 0,
                "consensus_rate": 0.0,
                "avg_rounds": 0.0,
                "outcomes": {}
            }
        
        consensus_count = sum(1 for r in self.negotiation_history if r.consensus_reached)
        total_rounds = sum(len(r.rounds) for r in self.negotiation_history)
        
        outcomes = {}
        for r in self.negotiation_history:
            decision = r.final_decision or "pending"
            outcomes[decision] = outcomes.get(decision, 0) + 1
        
        return {
            "total_negotiations": total,
            "consensus_rate": consensus_count / total,
            "avg_rounds": total_rounds / total,
            "outcomes": outcomes
        }
