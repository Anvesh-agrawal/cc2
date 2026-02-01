"""
Vanta: Agentic AI for Smart Payment Operations
=====================================================

A real-time payment operations manager that observes payment behavior,
reasons about patterns, decides on interventions, acts with guardrails,
and learns from outcomes.

Run with: streamlit run app.py
"""

import streamlit as st
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import threading
from collections import deque

# Configure page
st.set_page_config(
    page_title="Vanta | Agentic Payments",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import components
from config import config, PaymentMethod, ActionType
from core.simulator import PaymentSimulator
from core.pattern_detector import PatternDetector
from core.bayesian_router import BayesianRouter
from core.action_executor import ActionExecutor
from core.learning_engine import LearningEngine
from core.persistence import StatePersistence
from agents.optimizer import OptimizerAgent
from agents.risk_officer import RiskOfficerAgent
from agents.negotiator import NegotiationEngine
from agents.payload_mutator import PayloadMutatorAgent
from models.transaction import Transaction, TransactionBatch
from models.hypothesis import ActionRecommendation

# Import UI components
from ui.dashboard import (
    render_sidebar,
    render_dashboard,
    render_dashboard_header,
    render_pattern_alerts,
    render_transaction_feed,
    render_action_history
)
from ui.agent_panel import (
    render_agent_panel,
    render_negotiation_panel,
    render_learning_insights,
    render_payload_mutations
)
from ui.metrics import (
    render_metrics,
    render_success_rate_chart,
    render_bank_performance,
    render_method_performance,
    render_charts
)


# =============================================================================
# CUSTOM STYLES
# =============================================================================

st.markdown("""
<style>
    /* =================================================================
       DESIGN TOKENS - Consistent spacing and colors
       ================================================================= */
    :root {
        /* Spacing scale (8px base) */
        --space-1: 0.25rem;
        --space-2: 0.5rem;
        --space-3: 0.75rem;
        --space-4: 1rem;
        --space-5: 1.25rem;
        --space-6: 1.5rem;
        --space-8: 2rem;
        
        /* Colors */
        --bg-primary: #0F172A;
        --bg-secondary: #1E293B;
        --bg-tertiary: #334155;
        --border-subtle: rgba(148, 163, 184, 0.1);
        --border-default: rgba(148, 163, 184, 0.2);
        
        /* Accent colors */
        --accent-primary: #8B5CF6;
        --accent-secondary: #6366F1;
        --accent-glow: rgba(139, 92, 246, 0.4);
        
        /* Semantic colors */
        --success: #10B981;
        --warning: #F59E0B;
        --error: #EF4444;
        --info: #3B82F6;
        
        /* Text */
        --text-primary: #F1F5F9;
        --text-secondary: #94A3B8;
        --text-muted: #64748B;
        
        /* Animation */
        --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
        --ease-in-out: cubic-bezier(0.65, 0, 0.35, 1);
        --spring: cubic-bezier(0.34, 1.56, 0.64, 1);
        --duration-fast: 120ms;
        --duration-normal: 180ms;
        --duration-slow: 250ms;
    }
    
    /* =================================================================
       KEYFRAME ANIMATIONS
       ================================================================= */
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    
    @keyframes slideUp {
        from { 
            opacity: 0; 
            transform: translateY(20px); 
        }
        to { 
            opacity: 1; 
            transform: translateY(0); 
        }
    }
    
    @keyframes slideInRight {
        from { 
            opacity: 0; 
            transform: translateX(30px); 
        }
        to { 
            opacity: 1; 
            transform: translateX(0); 
        }
    }
    
    /* Removed: @keyframes pulse - continuous animation causes visual noise */
    
    /* Removed: @keyframes shimmer - decorative loading effect */
    
    /* Removed: @keyframes glow - continuous animation causes performance issues */
    
    @keyframes scaleIn {
        from { 
            opacity: 0; 
            transform: scale(0.95); 
        }
        to { 
            opacity: 1; 
            transform: scale(1); 
        }
    }
    
    /* Removed: @keyframes float - continuous animation is distracting */
    
    @keyframes countUp {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* =================================================================
       BASE STYLES
       ================================================================= */
    .stApp {
        background: linear-gradient(180deg, var(--bg-primary) 0%, var(--bg-secondary) 100%);
    }
    
    /* Sidebar with glassmorphism */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(30, 41, 59, 0.95) 0%, rgba(15, 23, 42, 0.95) 100%);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border-right: 1px solid var(--border-subtle);
        animation: fadeIn var(--duration-slow) var(--ease-out);
    }
    
    /* =================================================================
       METRIC CARDS - Animated entrance
       ================================================================= */
    .stMetric {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.8) 100%);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        padding: var(--space-4);
        border-radius: var(--space-3);
        border: 1px solid var(--border-subtle);
        animation: slideUp var(--duration-normal) var(--ease-out);
        transition: all var(--duration-fast) var(--ease-out);
    }
    
    .stMetric:hover {
        border-color: rgba(139, 92, 246, 0.3);
        transform: translateY(-1px);
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    }
    
    /* =================================================================
       BUTTONS - Interactive with feedback
       ================================================================= */
    .stButton > button {
        background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%);
        color: white;
        border: none;
        border-radius: var(--space-2);
        padding: var(--space-2) var(--space-4);
        font-weight: 600;
        transition: all var(--duration-fast) var(--ease-out);
        position: relative;
        overflow: hidden;
    }
    
    .stButton > button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        transition: left var(--duration-slow) var(--ease-out);
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);
    }
    
    .stButton > button:hover::before {
        left: 100%;
    }
    
    .stButton > button:active {
        transform: translateY(0) scale(0.98);
    }
    
    /* =================================================================
       TABS - Smooth transitions
       ================================================================= */
    .stTabs [data-baseweb="tab-list"] {
        gap: var(--space-2);
        background: rgba(30, 41, 59, 0.6);
        backdrop-filter: blur(10px);
        padding: var(--space-2);
        border-radius: var(--space-3);
        border: 1px solid var(--border-subtle);
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: var(--text-secondary);
        border-radius: var(--space-2);
        padding: var(--space-2) var(--space-4);
        transition: all var(--duration-fast) var(--ease-out);
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(139, 92, 246, 0.1);
        color: var(--text-primary);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%) !important;
        color: white !important;
    }
    
    /* =================================================================
       EXPANDERS - Smooth open/close
       ================================================================= */
    .streamlit-expanderHeader {
        background: rgba(30, 41, 59, 0.6);
        border-radius: var(--space-2);
        border: 1px solid var(--border-subtle);
        transition: all var(--duration-fast) var(--ease-out);
    }
    
    .streamlit-expanderHeader:hover {
        background: rgba(30, 41, 59, 0.8);
        border-color: var(--border-default);
    }
    
    /* =================================================================
       INPUTS - Enhanced focus states
       ================================================================= */
    .stSelectbox > div > div,
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input {
        background: rgba(30, 41, 59, 0.6) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: var(--space-2) !important;
        transition: all var(--duration-fast) var(--ease-out) !important;
    }
    
    .stSelectbox > div > div:hover,
    .stTextInput > div > div > input:hover,
    .stNumberInput > div > div > input:hover {
        border-color: var(--border-default) !important;
    }
    
    .stSelectbox > div > div:focus-within,
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: var(--accent-primary) !important;
        box-shadow: 0 0 0 3px var(--accent-glow) !important;
    }
    
    /* =================================================================
       TOGGLE - Smooth switch
       ================================================================= */
    .stToggle > label > div {
        transition: all var(--duration-fast) var(--ease-out) !important;
    }
    
    /* =================================================================
       SLIDER - Enhanced track
       ================================================================= */
    .stSlider > div > div > div {
        background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary)) !important;
    }
    
    /* =================================================================
       DIVIDERS
       ================================================================= */
    hr {
        border-color: var(--border-subtle);
        opacity: 0.5;
    }
    
    /* =================================================================
       TYPOGRAPHY - Hierarchy
       ================================================================= */
    h1, h2, h3, h4, h5, h6 {
        color: var(--text-primary) !important;
        animation: fadeIn var(--duration-normal) var(--ease-out);
    }
    
    h1 { 
        letter-spacing: -0.02em; 
        font-weight: 700;
    }
    
    h2, h3 { 
        letter-spacing: -0.01em;
        font-weight: 600;
    }
    
    p, span, label {
        color: var(--text-secondary);
    }
    
    /* =================================================================
       SCROLLBAR - Styled
       ================================================================= */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--bg-primary);
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--bg-tertiary);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--text-muted);
    }
    
    /* =================================================================
       CUSTOM COMPONENT ANIMATIONS
       ================================================================= */
    .metric-card {
        transition: all var(--duration-fast) var(--ease-out);
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.25);
    }
    
    /* Removed entrance animations from frequently-updating elements */
    .transaction-item {
        transition: all var(--duration-fast) var(--ease-out);
    }
    
    .pattern-alert {
        transition: all var(--duration-fast) var(--ease-out);
    }
    
    .action-card {
        transition: all var(--duration-fast) var(--ease-out);
    }
    
    .action-card:hover {
        transform: translateX(2px);
    }
    
    /* Status indicator - simple colored dot, no animation */
    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
    }
    
    /* =================================================================
       HIDE STREAMLIT BRANDING
       ================================================================= */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================

def init_session_state():
    """Initialize all session state variables."""
    
    if "initialized" not in st.session_state:
        # Core components
        st.session_state.simulator = PaymentSimulator()
        st.session_state.detector = PatternDetector()
        st.session_state.router = BayesianRouter()
        st.session_state.executor = ActionExecutor()
        st.session_state.learner = LearningEngine()
        st.session_state.persistence = StatePersistence()
        
        # Restore router state from database (learning persistence)
        try:
            st.session_state.persistence.restore_router_state(st.session_state.router)
        except Exception as e:
            pass  # First run, no state to restore
        
        # Agents
        st.session_state.optimizer = OptimizerAgent()
        st.session_state.risk_officer = RiskOfficerAgent()
        st.session_state.negotiator = NegotiationEngine(
            st.session_state.optimizer,
            st.session_state.risk_officer
        )
        st.session_state.payload_mutator = PayloadMutatorAgent()
        
        # Register action handlers
        _register_action_handlers()
        
        # State
        st.session_state.is_running = False
        st.session_state.transactions = deque(maxlen=500)
        st.session_state.historical_metrics = deque(maxlen=100)
        st.session_state.current_batch = TransactionBatch()
        
        # Agent ON/OFF State with dual margin tracking
        st.session_state.agent_enabled = True  # Start with agent ON
        st.session_state.agent_margin = 0.0    # Margin earned with smart routing
        st.session_state.naive_margin = 0.0    # What naive routing would earn
        
        # Counters
        st.session_state.tick_count = 0
        st.session_state.last_chaos_check = datetime.now()
        st.session_state.last_agent_check = datetime.now()
        st.session_state.last_save_time = datetime.now()
        
        st.session_state.initialized = True


def _register_action_handlers():
    """Register action handlers with the executor."""
    executor = st.session_state.executor
    router = st.session_state.router
    
    # Reroute traffic handler
    def handle_reroute(action: ActionRecommendation) -> Dict:
        from_entity = action.parameters.get("from_entity", "")
        to_entity = action.parameters.get("to_entity", "")
        traffic_pct = action.parameters.get("traffic_percentage", 10) / 100
        
        # Adjust traffic weights
        if from_entity in router.traffic_weights:
            router.adjust_traffic_weight(from_entity, 1.0 - traffic_pct)
        
        return {"success": True, "message": f"Routed {traffic_pct*100:.0f}% traffic from {from_entity}"}
    
    def rollback_reroute(action: ActionRecommendation, pre_state: Dict) -> Dict:
        from_entity = action.parameters.get("from_entity", "")
        router.adjust_traffic_weight(from_entity, 1.0)
        return {"success": True, "message": "Rollback: restored traffic weights"}
    
    executor.register_handler(ActionType.REROUTE_TRAFFIC, handle_reroute, rollback_reroute)
    
    # Retry strategy handler
    def handle_retry(action: ActionRecommendation) -> Dict:
        # In a real system, this would update retry configuration
        return {"success": True, "message": "Retry strategy updated"}
    
    executor.register_handler(ActionType.ADJUST_RETRY_STRATEGY, handle_retry)
    
    # Suppress path handler
    def handle_suppress(action: ActionRecommendation) -> Dict:
        path = action.parameters.get("path", "")
        duration = action.parameters.get("duration_seconds", 180)
        reason = action.parameters.get("reason", "Agent decision")
        
        router.suppress_route(path, duration, reason)
        return {"success": True, "message": f"Suppressed {path} for {duration}s"}
    
    def rollback_suppress(action: ActionRecommendation, pre_state: Dict) -> Dict:
        path = action.parameters.get("path", "")
        router.unsuppress_route(path)
        return {"success": True, "message": f"Unsuppressed {path}"}
    
    executor.register_handler(ActionType.SUPPRESS_PATH, handle_suppress, rollback_suppress)
    
    # Circuit break handler
    def handle_circuit_break(action: ActionRecommendation) -> Dict:
        entity = action.parameters.get("entity", "")
        router.suppress_route(f"{entity}_*", 300, "Circuit breaker activated")
        return {"success": True, "message": f"Circuit breaker activated on {entity}"}
    
    executor.register_handler(ActionType.CIRCUIT_BREAK, handle_circuit_break)
    
    # Recommend method handler
    def handle_recommend(action: ActionRecommendation) -> Dict:
        return {"success": True, "message": "Method recommendation displayed"}
    
    executor.register_handler(ActionType.RECOMMEND_METHOD, handle_recommend)
    
    # Alert ops handler
    def handle_alert(action: ActionRecommendation) -> Dict:
        return {"success": True, "message": "Ops team alerted"}
    
    executor.register_handler(ActionType.ALERT_OPS, handle_alert)
    
    # Payload mutation handler
    def handle_mutate_payload(action: ActionRecommendation) -> Dict:
        return {"success": True, "message": "Payload mutated and retried"}
    
    executor.register_handler(ActionType.MUTATE_PAYLOAD, handle_mutate_payload)


# =============================================================================
# SIMULATION LOOP
# =============================================================================

def run_simulation_tick():
    """Run one tick of the simulation."""
    if not st.session_state.is_running:
        return
    
    st.session_state.tick_count += 1
    now = datetime.now()
    
    # Generate transactions
    num_txns = int(config.simulation.transactions_per_second)
    for _ in range(num_txns):
        txn = st.session_state.simulator.generate_transaction()
        
        # === PAYLOAD POLYMORPHISM ENGINE ===
        # If transaction failed with payload error, try to mutate and retry
        mutator = st.session_state.payload_mutator
        if txn.is_failed and txn.error_code and mutator.can_mutate(txn.error_code, txn.gateway):
            # Prepare payload for mutation
            payload = {
                "address_line1": txn.address_line1,
                "phone_number": txn.phone_number,
                "customer_name": txn.customer_name
            }
            
            # Attempt mutation
            mutated_payload, mutation_record = mutator.mutate_payload(
                txn.id, txn.gateway, txn.error_code, payload
            )
            
            if mutation_record:
                # Simulate retry with mutated payload (higher success rate)
                import random
                retry_success = random.random() < 0.75  # 75% success after mutation
                
                # Record outcome
                mutator.record_outcome(mutation_record.id, retry_success)
                
                # If mutation succeeded, update transaction status
                if retry_success:
                    from config import TransactionStatus
                    txn.status = TransactionStatus.SUCCESS
                    txn.was_mutated = True
                    txn.mutation_id = mutation_record.id
                    txn.error_code = None
                    txn.error_message = None
        
        # Process through detector
        patterns = st.session_state.detector.process_transaction(txn)
        
        # Update router stats
        st.session_state.router.update_route(txn)
        
        # Track margins based on agent ON/OFF state
        if txn.is_successful:
            # Get gateway fee (smart routing would pick low-fee gateway)
            smart_fee = st.session_state.router.provider_fees.get(txn.gateway, 0.02)
            # Naive routing would use highest-fee gateway
            naive_fee = max(st.session_state.router.provider_fees.values())
            
            smart_profit = txn.amount * (1 - smart_fee)
            naive_profit = txn.amount * (1 - naive_fee)
            
            if st.session_state.agent_enabled:
                # Agent ON: We're using smart routing
                st.session_state.agent_margin += smart_profit
                st.session_state.naive_margin += naive_profit  # What we'd lose without agent
            else:
                # Agent OFF: We're using naive routing but track what agent would earn
                st.session_state.naive_margin += naive_profit
                st.session_state.agent_margin += smart_profit  # What we're missing
        
        # Store transaction
        st.session_state.transactions.append(txn.to_dict())
        st.session_state.current_batch.transactions.append(txn)
    
    # Periodically inject chaos
    if (now - st.session_state.last_chaos_check).total_seconds() > 10:
        st.session_state.simulator.inject_random_chaos()
        st.session_state.last_chaos_check = now
    
    # Periodically run agent decision loop (only if agent is ON)
    if st.session_state.agent_enabled and (now - st.session_state.last_agent_check).total_seconds() > 5:
        _run_agent_decision_loop()
        st.session_state.last_agent_check = now
    
    # Periodically save state (every 60 seconds)
    if (now - st.session_state.last_save_time).total_seconds() > 60:
        try:
            st.session_state.persistence.save_all_router_state(st.session_state.router)
        except Exception:
            pass  # Ignore save errors
        st.session_state.last_save_time = now
    
    # Record metrics
    _record_metrics()


def _run_agent_decision_loop():
    """Run the agent observe → reason → decide → act loop."""
    detector = st.session_state.detector
    optimizer = st.session_state.optimizer
    negotiator = st.session_state.negotiator
    executor = st.session_state.executor
    learner = st.session_state.learner
    
    # Get current state
    patterns = detector.active_patterns
    hypotheses = detector.active_hypotheses
    current_metrics = _get_current_metrics()
    
    if not patterns or not hypotheses:
        return
    
    # Get actionable hypotheses
    actionable = [h for h in hypotheses if h.is_actionable]
    
    if not actionable:
        return
    
    # Take the highest confidence hypothesis
    best_hypothesis = max(actionable, key=lambda h: h.confidence)
    
    # Find the corresponding pattern
    pattern = next(
        (p for p in patterns if p.id == best_hypothesis.pattern_id),
        patterns[0] if patterns else None
    )
    
    if not pattern:
        return
    
    # Get route options
    route_options = st.session_state.router.get_all_routes()
    
    # Optimizer proposes an action
    action = optimizer.propose_action(pattern, best_hypothesis, current_metrics, route_options)
    
    if not action:
        return
    
    # Negotiate with Risk Officer
    result = negotiator.negotiate(action, current_metrics)
    
    if result.success and result.final_action:
        # Execute the action
        success, message, record = executor.execute(result.final_action)
        
        if success and record:
            # Track outcome after a delay (in real system)
            # For demo, we'll track immediately with simulated metrics
            post_metrics = current_metrics.copy()
            post_metrics["success_rate"] = min(1.0, current_metrics.get("success_rate", 0.9) + 0.02)
            
            outcome = learner.record_outcome(
                result.final_action,
                current_metrics,
                post_metrics,
                len(st.session_state.current_batch.transactions)
            )
            
            # Validate hypothesis
            learner.validate_hypothesis(best_hypothesis, outcome)
            
            # Record action with Risk Officer
            st.session_state.risk_officer.record_action(result.final_action)


def _record_metrics():
    """Record current metrics to historical data."""
    metrics = _get_current_metrics()
    metrics["timestamp"] = datetime.now()
    st.session_state.historical_metrics.append(metrics)


def _get_current_metrics() -> Dict:
    """Calculate current metrics from recent transactions."""
    recent = list(st.session_state.transactions)[-100:]
    
    if not recent:
        return {
            "success_rate": 0.0,
            "avg_latency": 0.0,
            "retry_rate": 0.0,
            "error_rate": 0.0,
            "throughput": 0
        }
    
    successes = sum(1 for t in recent if t.get("status") == "success")
    retries = sum(1 for t in recent if t.get("is_retry"))
    errors = sum(1 for t in recent if t.get("status") in ["failure", "timeout"])
    total_latency = sum(t.get("latency_ms", 0) for t in recent)
    
    return {
        "success_rate": successes / len(recent),
        "avg_latency": total_latency / len(recent),
        "retry_rate": retries / len(recent),
        "error_rate": errors / len(recent),
        "throughput": int(config.simulation.transactions_per_second)
    }


# =============================================================================
# CALLBACKS
# =============================================================================

def on_toggle_simulation():
    """Toggle simulation running state."""
    st.session_state.is_running = not st.session_state.is_running


def on_inject_chaos(chaos_type: str):
    """Inject a chaos scenario."""
    scenario = st.session_state.simulator.inject_chaos(chaos_type)
    if scenario:
        st.toast(f"💥 Injected: {scenario.description}", icon="🔥")


def on_clear_chaos():
    """Clear all chaos scenarios."""
    st.session_state.simulator.clear_chaos()
    st.toast("✅ Chaos cleared", icon="🗑️")


def on_approve_action(action_id: str):
    """Approve a pending action."""
    success, message, record = st.session_state.executor.approve_action(action_id)
    if success:
        st.toast(f"✅ Action approved: {message}", icon="✅")
    else:
        st.toast(f"❌ Approval failed: {message}", icon="❌")


def on_reject_action(action_id: str):
    """Reject a pending action."""
    st.session_state.executor.reject_action(action_id, "User rejected")
    st.toast("❌ Action rejected", icon="❌")


def on_chaos_level_change(level: float):
    """Update chaos level in simulation config."""
    config.simulation.chaos_level = level


def on_agent_toggle(enabled: bool):
    """Toggle agent ON/OFF."""
    st.session_state.agent_enabled = enabled
    if enabled:
        st.toast("🤖 Agent ENABLED - using smart EV-optimized routing", icon="✅")
    else:
        st.toast("⚠️ Agent DISABLED - using naive routing", icon="⚠️")


# =============================================================================
# MAIN APP
# =============================================================================

def main():
    """Main application entry point."""
    
    # Initialize
    init_session_state()
    
    # Run simulation tick
    run_simulation_tick()
    
    # Get current state
    current_metrics = _get_current_metrics()
    patterns = st.session_state.detector.get_active_patterns()
    transactions = list(st.session_state.transactions)
    actions = st.session_state.executor.get_executed_actions()
    scenarios = st.session_state.simulator.get_active_scenarios()
    
    # Render sidebar
    sidebar_state = render_sidebar(
        simulator_stats=st.session_state.simulator.get_stats(),
        detector_stats=st.session_state.detector.get_stats(),
        router_stats=st.session_state.router.get_stats(),
        learning_stats=st.session_state.learner.get_stats(),
        on_inject_chaos=on_inject_chaos,
        on_clear_chaos=on_clear_chaos,
        on_toggle_simulation=on_toggle_simulation,
        on_chaos_level_change=on_chaos_level_change,
        on_agent_toggle=on_agent_toggle,
        is_running=st.session_state.is_running,
        agent_enabled=st.session_state.agent_enabled,
        agent_margin=st.session_state.agent_margin,
        naive_margin=st.session_state.naive_margin
    )
    
    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "Dashboard",
        "Agent Center",
        "Analytics",
        "Learning"
    ])
    
    with tab1:
        render_dashboard(
            current_metrics=current_metrics,
            patterns=patterns,
            transactions=transactions,
            actions=actions,
            scenarios=scenarios
        )
    
    with tab2:
        render_agent_panel(
            optimizer_stats=st.session_state.optimizer.get_stats(),
            risk_officer_stats=st.session_state.risk_officer.get_stats(),
            negotiation_stats=st.session_state.negotiator.get_stats(),
            pending_approvals=st.session_state.executor.get_pending_approvals(),
            on_approve=on_approve_action,
            on_reject=on_reject_action
        )
        
        st.divider()
        
        render_negotiation_panel(
            st.session_state.negotiator.get_recent_negotiations()
        )
        
        st.divider()
        
        # Payload Polymorphism Engine panel
        render_payload_mutations(
            mutations=st.session_state.payload_mutator.get_recent_mutations(),
            mutator_stats=st.session_state.payload_mutator.get_stats()
        )
    
    with tab3:
        # Get analytics data
        bank_stats = {}
        method_stats = {}
        error_data = {}
        
        if st.session_state.current_batch.count > 0:
            bank_stats = st.session_state.current_batch.get_bank_stats()
            method_stats = st.session_state.current_batch.get_method_stats()
            error_data = st.session_state.current_batch.get_error_distribution()
        
        route_data = st.session_state.router.get_all_routes()
        
        render_charts(
            historical_data=list(st.session_state.historical_metrics),
            transactions=transactions,
            bank_stats=bank_stats,
            method_stats=method_stats,
            error_data=error_data,
            route_data=route_data
        )
    
    with tab4:
        render_learning_insights(
            learnings=st.session_state.learner.get_recent_learnings(),
            action_stats=st.session_state.learner.get_action_type_stats()
        )
        
        st.divider()
        
        # Strategy display
        st.subheader("📋 Adaptive Strategies")
        
        strategies = st.session_state.learner.get_all_strategies()
        
        for name, state in strategies.items():
            with st.expander(f"🎯 {name.replace('_', ' ').title()}", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Parameters:**")
                    for param, value in state["parameters"].items():
                        st.caption(f"• {param}: {value}")
                with col2:
                    st.metric("Updates", state["updates_count"])
                    st.metric("Performance", f"{state['performance_score']:.0%}")
    
    # Auto-refresh when running
    if st.session_state.is_running:
        time.sleep(0.5)
        st.rerun()


if __name__ == "__main__":
    main()
