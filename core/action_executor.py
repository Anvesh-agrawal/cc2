"""
Action Executor
===============
Guardrailed action execution with rate limiting and rollback capabilities.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from collections import deque
import threading

from config import ActionType, AutonomyLevel, ExecutorConfig, RiskOfficerConfig, config
from models.hypothesis import ActionRecommendation, ActionOutcome


@dataclass
class ActionRecord:
    """Record of an executed action for audit trail."""
    action: ActionRecommendation
    executed_at: datetime
    executor: str
    pre_state: Dict[str, Any]
    post_state: Optional[Dict[str, Any]] = None
    outcome: Optional[ActionOutcome] = None
    was_rolled_back: bool = False
    rollback_at: Optional[datetime] = None
    rollback_reason: Optional[str] = None


class ActionExecutor:
    """
    Executes actions with guardrails, rate limiting, and rollback support.
    
    Features:
    - Autonomy level enforcement
    - Rate limiting per time window
    - Pre/post state capture for rollback
    - Full audit trail
    - Automatic rollback on failure detection
    """
    
    def __init__(
        self,
        executor_config: ExecutorConfig = None,
        risk_config: RiskOfficerConfig = None
    ):
        self.executor_config = executor_config or ExecutorConfig()
        self.risk_config = risk_config or RiskOfficerConfig()
        
        # Action history for rate limiting
        self.recent_actions: deque = deque(maxlen=100)
        
        # Pending approvals
        self.pending_approvals: Dict[str, ActionRecommendation] = {}
        
        # Executed actions (for rollback)
        self.executed_actions: Dict[str, ActionRecord] = {}
        
        # Action handlers (registered externally)
        self.action_handlers: Dict[ActionType, Callable] = {}
        self.rollback_handlers: Dict[ActionType, Callable] = {}
        
        # State capture functions (registered externally)
        self.state_capturer: Optional[Callable] = None
        
        # Lock for thread safety
        self._lock = threading.Lock()
        
        # Callbacks for notifications
        self.on_action_executed: Optional[Callable[[ActionRecord], None]] = None
        self.on_approval_required: Optional[Callable[[ActionRecommendation], None]] = None
        self.on_rollback: Optional[Callable[[ActionRecord, str], None]] = None
    
    def register_handler(
        self,
        action_type: ActionType,
        handler: Callable,
        rollback_handler: Callable = None
    ):
        """Register a handler for an action type."""
        self.action_handlers[action_type] = handler
        if rollback_handler:
            self.rollback_handlers[action_type] = rollback_handler
    
    def register_state_capturer(self, capturer: Callable):
        """Register a function to capture system state."""
        self.state_capturer = capturer
    
    def can_execute_autonomously(self, action: ActionRecommendation) -> Tuple[bool, str]:
        """Check if an action can be executed autonomously."""
        # Check autonomy level
        autonomy_str = self.executor_config.autonomy_levels.get(
            action.action_type.value,
            AutonomyLevel.MANUAL.value
        )
        
        if autonomy_str == AutonomyLevel.MANUAL.value:
            return False, "Action type requires manual approval"
        
        # Check rate limiting
        if not self._check_rate_limit():
            return False, f"Rate limit exceeded: max {self.risk_config.max_actions_per_window} actions per {self.risk_config.action_window_seconds}s"
        
        # Check action-specific constraints
        if action.action_type == ActionType.REROUTE_TRAFFIC:
            traffic_pct = action.parameters.get("traffic_percentage", 0)
            if traffic_pct > self.risk_config.traffic_shift_veto_threshold * 100:
                return False, f"Traffic shift {traffic_pct}% exceeds autonomous limit"
        
        # Check risk score
        if action.risk_score > 0.7:
            return False, f"Risk score {action.risk_score:.2f} too high for autonomous execution"
        
        return True, "OK"
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        now = datetime.now()
        window_start = now - timedelta(seconds=self.risk_config.action_window_seconds)
        
        recent_count = sum(
            1 for record in self.executed_actions.values()
            if record.executed_at > window_start
        )
        
        return recent_count < self.risk_config.max_actions_per_window
    
    def execute(
        self,
        action: ActionRecommendation,
        force: bool = False
    ) -> Tuple[bool, str, Optional[ActionRecord]]:
        """
        Execute an action with guardrails.
        
        Args:
            action: The action to execute
            force: If True, bypass autonomy checks (for human-approved actions)
        
        Returns:
            Tuple of (success, message, action_record)
        """
        with self._lock:
            # Check if we can execute
            if not force:
                can_execute, reason = self.can_execute_autonomously(action)
                if not can_execute:
                    # Queue for approval if semi-autonomous
                    autonomy_str = self.executor_config.autonomy_levels.get(
                        action.action_type.value,
                        AutonomyLevel.MANUAL.value
                    )
                    if autonomy_str == AutonomyLevel.SEMI_AUTONOMOUS.value:
                        self.pending_approvals[action.id] = action
                        if self.on_approval_required:
                            self.on_approval_required(action)
                        return False, f"Queued for approval: {reason}", None
                    return False, f"Cannot execute: {reason}", None
            
            # Check handler exists
            handler = self.action_handlers.get(action.action_type)
            if not handler:
                return False, f"No handler registered for {action.action_type.value}", None
            
            # Capture pre-state
            pre_state = {}
            if self.state_capturer:
                try:
                    pre_state = self.state_capturer()
                except Exception as e:
                    pre_state = {"error": str(e)}
            
            # Execute action
            try:
                result = handler(action)
                success = result.get("success", False)
                message = result.get("message", "")
            except Exception as e:
                success = False
                message = f"Execution error: {str(e)}"
            
            # Create record
            record = ActionRecord(
                action=action,
                executed_at=datetime.now(),
                executor="autonomous" if not force else "human_approved",
                pre_state=pre_state
            )
            
            if success:
                action.is_executed = True
                action.execution_time = datetime.now()
                
                # Capture post-state
                if self.state_capturer:
                    try:
                        record.post_state = self.state_capturer()
                    except:
                        pass
                
                # Store for potential rollback
                self.executed_actions[action.id] = record
                self.recent_actions.append(record)
                
                # Notify
                if self.on_action_executed:
                    self.on_action_executed(record)
            
            # Remove from pending if it was there
            if action.id in self.pending_approvals:
                del self.pending_approvals[action.id]
            
            return success, message, record
    
    def approve_action(self, action_id: str) -> Tuple[bool, str, Optional[ActionRecord]]:
        """Approve and execute a pending action."""
        if action_id not in self.pending_approvals:
            return False, "Action not found in pending approvals", None
        
        action = self.pending_approvals[action_id]
        action.is_approved = True
        action.approved_by = action.proposed_by  # In real system, would be the approver
        
        return self.execute(action, force=True)
    
    def reject_action(self, action_id: str, reason: str = "") -> bool:
        """Reject a pending action."""
        if action_id in self.pending_approvals:
            del self.pending_approvals[action_id]
            return True
        return False
    
    def rollback(self, action_id: str, reason: str = "") -> Tuple[bool, str]:
        """Rollback a previously executed action."""
        with self._lock:
            if action_id not in self.executed_actions:
                return False, "Action not found in executed actions"
            
            record = self.executed_actions[action_id]
            
            if record.was_rolled_back:
                return False, "Action was already rolled back"
            
            if not record.action.can_rollback:
                return False, "Action does not support rollback"
            
            # Get rollback handler
            rollback_handler = self.rollback_handlers.get(record.action.action_type)
            if not rollback_handler:
                return False, f"No rollback handler for {record.action.action_type.value}"
            
            # Execute rollback
            try:
                result = rollback_handler(record.action, record.pre_state)
                success = result.get("success", False)
                message = result.get("message", "")
            except Exception as e:
                success = False
                message = f"Rollback error: {str(e)}"
            
            if success:
                record.was_rolled_back = True
                record.rollback_at = datetime.now()
                record.rollback_reason = reason
                
                if self.on_rollback:
                    self.on_rollback(record, reason)
            
            return success, message
    
    def check_for_auto_rollback(self, outcome: ActionOutcome) -> Optional[str]:
        """
        Check if an action outcome triggers automatic rollback.
        
        Returns action_id if rollback is needed, None otherwise.
        """
        if not self.executor_config.auto_rollback_on_failure:
            return None
        
        # Check success rate drop
        if outcome.success_rate_delta < -self.risk_config.success_rate_drop_trigger:
            return outcome.action_id
        
        # Check latency spike
        if outcome.pre_avg_latency > 0:
            latency_ratio = outcome.post_avg_latency / outcome.pre_avg_latency
            if latency_ratio > self.risk_config.latency_spike_trigger:
                return outcome.action_id
        
        return None
    
    def record_outcome(self, action_id: str, outcome: ActionOutcome):
        """Record the outcome of an action."""
        if action_id in self.executed_actions:
            self.executed_actions[action_id].outcome = outcome
            
            # Check for auto-rollback
            needs_rollback = self.check_for_auto_rollback(outcome)
            if needs_rollback:
                self.rollback(action_id, "Auto-rollback: performance degradation detected")
    
    def get_pending_approvals(self) -> List[Dict]:
        """Get list of actions pending approval."""
        return [action.to_dict() for action in self.pending_approvals.values()]
    
    def get_executed_actions(self, limit: int = 50) -> List[Dict]:
        """Get recent executed actions."""
        actions = sorted(
            self.executed_actions.values(),
            key=lambda x: x.executed_at,
            reverse=True
        )[:limit]
        
        return [
            {
                "action_id": r.action.id,
                "action_type": r.action.action_type.value,
                "description": r.action.description,
                "executed_at": r.executed_at,
                "executor": r.executor,
                "was_rolled_back": r.was_rolled_back,
                "has_outcome": r.outcome is not None,
                "outcome_success": r.outcome.was_successful if r.outcome else None
            }
            for r in actions
        ]
    
    def get_stats(self) -> Dict:
        """Get executor statistics."""
        now = datetime.now()
        window_start = now - timedelta(seconds=self.risk_config.action_window_seconds)
        
        recent_actions = [
            r for r in self.executed_actions.values()
            if r.executed_at > window_start
        ]
        
        rollbacks = [r for r in self.executed_actions.values() if r.was_rolled_back]
        
        return {
            "total_executed": len(self.executed_actions),
            "pending_approvals": len(self.pending_approvals),
            "actions_in_window": len(recent_actions),
            "window_limit": self.risk_config.max_actions_per_window,
            "total_rollbacks": len(rollbacks),
            "rollback_rate": len(rollbacks) / max(1, len(self.executed_actions))
        }
