"""
Dashboard Components
====================
Main dashboard and sidebar UI components.
"""

import streamlit as st
from datetime import datetime
from typing import Dict, List, Any

from config import config


def render_sidebar(
    simulator_stats: Dict,
    detector_stats: Dict,
    router_stats: Dict,
    learning_stats: Dict,
    on_inject_chaos: callable = None,
    on_clear_chaos: callable = None,
    on_toggle_simulation: callable = None,
    is_running: bool = False
) -> Dict[str, Any]:
    """Render the sidebar with controls and stats."""
    
    with st.sidebar:
        # Logo and title
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0;">
            <h1 style="
                background: linear-gradient(135deg, #8B5CF6 0%, #6366F1 50%, #3B82F6 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                font-size: 2rem;
                font-weight: 800;
                margin: 0;
            ">⚡ Antigravity</h1>
            <p style="color: #94A3B8; font-size: 0.85rem; margin-top: 0.5rem;">
                Agentic Payment Operations
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        # Simulation Controls
        st.subheader("🎮 Simulation Control")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                "▶️ Start" if not is_running else "⏸️ Pause",
                use_container_width=True,
                type="primary" if not is_running else "secondary"
            ):
                if on_toggle_simulation:
                    on_toggle_simulation()
        
        with col2:
            if st.button("🗑️ Clear", use_container_width=True):
                if on_clear_chaos:
                    on_clear_chaos()
        
        # Chaos Injection
        st.subheader("💥 Chaos Injection")
        
        chaos_type = st.selectbox(
            "Scenario Type",
            options=[
                "issuer_degradation",
                "retry_storm",
                "method_fatigue",
                "latency_spike",
                "gateway_issues",
                "peak_hour_load"
            ],
            format_func=lambda x: x.replace("_", " ").title()
        )
        
        if st.button("🔥 Inject Chaos", use_container_width=True, type="primary"):
            if on_inject_chaos:
                on_inject_chaos(chaos_type)
        
        st.divider()
        
        # System Stats
        st.subheader("📊 System Stats")
        
        # Simulator stats
        with st.expander("🔄 Simulator", expanded=True):
            st.metric("Total Transactions", simulator_stats.get("total_transactions", 0))
            st.metric("Active Scenarios", simulator_stats.get("active_scenarios", 0))
            st.metric("Pending Retries", simulator_stats.get("pending_retries", 0))
        
        # Detector stats
        with st.expander("🔍 Pattern Detector"):
            st.metric("Active Patterns", detector_stats.get("active_patterns", 0))
            st.metric("Active Hypotheses", detector_stats.get("active_hypotheses", 0))
            st.metric("Total Detected", detector_stats.get("total_patterns_detected", 0))
        
        # Router stats
        with st.expander("🎯 Router"):
            st.metric("Total Routes", router_stats.get("total_routes", 0))
            st.metric("Active Routes", router_stats.get("active_routes", 0))
            st.metric("Suppressed", router_stats.get("suppressed_routes", 0))
        
        # Learning stats
        with st.expander("🧠 Learning Engine"):
            st.metric("Total Outcomes", learning_stats.get("total_outcomes", 0))
            accuracy = learning_stats.get("hypothesis_accuracy", {}).get("accuracy", 0)
            st.metric("Hypothesis Accuracy", f"{accuracy:.1%}")
            st.metric("Strategy Updates", learning_stats.get("strategy_updates", 0))
        
        st.divider()
        
        # Time
        st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')}")
    
    return {"chaos_type": chaos_type}


def render_dashboard_header(current_metrics: Dict[str, float]):
    """Render the main dashboard header with key metrics."""
    
    st.markdown("""
    <style>
        .metric-card {
            background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
            border-radius: 1rem;
            padding: 1.5rem;
            border: 1px solid #334155;
            text-align: center;
        }
        .metric-value {
            font-size: 2.5rem;
            font-weight: 700;
            margin: 0;
        }
        .metric-label {
            color: #94A3B8;
            font-size: 0.9rem;
            margin-top: 0.5rem;
        }
        .metric-delta {
            font-size: 0.85rem;
            margin-top: 0.25rem;
        }
        .delta-positive { color: #10B981; }
        .delta-negative { color: #EF4444; }
    </style>
    """, unsafe_allow_html=True)
    
    cols = st.columns(4)
    
    success_rate = current_metrics.get("success_rate", 0.0)
    avg_latency = current_metrics.get("avg_latency", 0)
    retry_rate = current_metrics.get("retry_rate", 0.0)
    throughput = current_metrics.get("throughput", 0)
    
    with cols[0]:
        color = "#10B981" if success_rate >= 0.9 else "#F59E0B" if success_rate >= 0.8 else "#EF4444"
        st.markdown(f"""
        <div class="metric-card">
            <p class="metric-value" style="color: {color};">{success_rate:.1%}</p>
            <p class="metric-label">Success Rate</p>
        </div>
        """, unsafe_allow_html=True)
    
    with cols[1]:
        color = "#10B981" if avg_latency < 1500 else "#F59E0B" if avg_latency < 2500 else "#EF4444"
        st.markdown(f"""
        <div class="metric-card">
            <p class="metric-value" style="color: {color};">{avg_latency:.0f}ms</p>
            <p class="metric-label">Avg Latency</p>
        </div>
        """, unsafe_allow_html=True)
    
    with cols[2]:
        color = "#10B981" if retry_rate < 0.1 else "#F59E0B" if retry_rate < 0.2 else "#EF4444"
        st.markdown(f"""
        <div class="metric-card">
            <p class="metric-value" style="color: {color};">{retry_rate:.1%}</p>
            <p class="metric-label">Retry Rate</p>
        </div>
        """, unsafe_allow_html=True)
    
    with cols[3]:
        st.markdown(f"""
        <div class="metric-card">
            <p class="metric-value" style="color: #8B5CF6;">{throughput}</p>
            <p class="metric-label">TPS</p>
        </div>
        """, unsafe_allow_html=True)


def render_pattern_alerts(patterns: List[Dict]):
    """Render active pattern alerts."""
    
    if not patterns:
        st.info("✅ No active patterns detected. System operating normally.")
        return
    
    for pattern in patterns[:5]:  # Show top 5
        severity = pattern.get("severity", 0)
        severity_label = pattern.get("severity_label", "LOW")
        
        if severity >= 0.8:
            alert_type = "error"
            icon = "🚨"
        elif severity >= 0.6:
            alert_type = "warning"
            icon = "⚠️"
        else:
            alert_type = "info"
            icon = "ℹ️"
        
        pattern_type = pattern.get("pattern_type", "unknown").replace("_", " ").title()
        entity = pattern.get("affected_entity", "Unknown")
        confidence = pattern.get("confidence", 0)
        
        with st.container():
            if alert_type == "error":
                st.error(f"{icon} **{pattern_type}** on `{entity}` | Severity: {severity_label} | Confidence: {confidence:.0%}")
            elif alert_type == "warning":
                st.warning(f"{icon} **{pattern_type}** on `{entity}` | Severity: {severity_label} | Confidence: {confidence:.0%}")
            else:
                st.info(f"{icon} **{pattern_type}** on `{entity}` | Severity: {severity_label} | Confidence: {confidence:.0%}")


def render_chaos_scenarios(scenarios: List[Dict]):
    """Render active chaos scenarios."""
    
    if not scenarios:
        return
    
    st.subheader("💥 Active Chaos Scenarios")
    
    for scenario in scenarios:
        remaining = scenario.get("remaining_seconds", 0)
        success_mod = scenario.get("success_rate_modifier", 1.0)
        latency_mod = scenario.get("latency_modifier", 1.0)
        
        with st.expander(f"🔥 {scenario.get('name', 'Unknown')}", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Remaining", f"{remaining:.0f}s")
            with col2:
                st.metric("Success Impact", f"{(1-success_mod)*100:.0f}% ↓")
            with col3:
                st.metric("Latency Impact", f"{(latency_mod-1)*100:.0f}% ↑")
            
            st.caption(scenario.get("description", ""))


def render_transaction_feed(transactions: List[Dict], max_display: int = 20):
    """Render live transaction feed."""
    
    if not transactions:
        st.caption("No transactions yet...")
        return
    
    # Create a styled transaction list
    for txn in transactions[-max_display:][::-1]:  # Reverse to show newest first
        status = txn.get("status", "pending")
        method = txn.get("payment_method", "").upper()
        bank = txn.get("issuer_bank", "")
        latency = txn.get("latency_ms", 0)
        amount = txn.get("amount", 0)
        is_retry = txn.get("is_retry", False)
        
        if status == "success":
            status_icon = "✅"
            status_color = "#10B981"
        elif status == "failure":
            status_icon = "❌"
            status_color = "#EF4444"
        elif status == "timeout":
            status_icon = "⏱️"
            status_color = "#F59E0B"
        else:
            status_icon = "⏳"
            status_color = "#6B7280"
        
        retry_badge = "🔄 " if is_retry else ""
        
        st.markdown(f"""
        <div style="
            display: flex;
            align-items: center;
            padding: 0.5rem;
            margin: 0.25rem 0;
            background: #1E293B;
            border-radius: 0.5rem;
            border-left: 3px solid {status_color};
            font-size: 0.85rem;
        ">
            <span style="margin-right: 0.5rem;">{status_icon}</span>
            <span style="color: #94A3B8; min-width: 80px;">{retry_badge}{method}</span>
            <span style="color: #E2E8F0; min-width: 80px;">{bank}</span>
            <span style="color: #94A3B8; min-width: 80px;">₹{amount:,.0f}</span>
            <span style="color: #94A3B8; margin-left: auto;">{latency:.0f}ms</span>
        </div>
        """, unsafe_allow_html=True)


def render_action_history(actions: List[Dict]):
    """Render action history."""
    
    if not actions:
        st.caption("No actions taken yet...")
        return
    
    for action in actions[:10]:
        action_type = action.get("action_type", "unknown").replace("_", " ").title()
        executed_at = action.get("executed_at", datetime.now())
        was_rolled_back = action.get("was_rolled_back", False)
        outcome_success = action.get("outcome_success")
        
        if was_rolled_back:
            status_icon = "↩️"
            status_text = "Rolled Back"
            color = "#F59E0B"
        elif outcome_success is True:
            status_icon = "✅"
            status_text = "Successful"
            color = "#10B981"
        elif outcome_success is False:
            status_icon = "❌"
            status_text = "Failed"
            color = "#EF4444"
        else:
            status_icon = "⏳"
            status_text = "Pending"
            color = "#6B7280"
        
        time_str = executed_at.strftime("%H:%M:%S") if isinstance(executed_at, datetime) else str(executed_at)[:8]
        
        st.markdown(f"""
        <div style="
            padding: 0.75rem;
            margin: 0.5rem 0;
            background: linear-gradient(90deg, {color}22 0%, transparent 100%);
            border-radius: 0.5rem;
            border-left: 3px solid {color};
        ">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: 600;">{status_icon} {action_type}</span>
                <span style="color: #94A3B8; font-size: 0.8rem;">{time_str}</span>
            </div>
            <div style="color: #94A3B8; font-size: 0.85rem; margin-top: 0.25rem;">
                {action.get("description", "")}
            </div>
            <div style="color: {color}; font-size: 0.8rem; margin-top: 0.25rem;">
                {status_text}
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_dashboard(
    current_metrics: Dict[str, float],
    patterns: List[Dict],
    transactions: List[Dict],
    actions: List[Dict],
    scenarios: List[Dict]
):
    """Render the main dashboard."""
    
    # Header metrics
    render_dashboard_header(current_metrics)
    
    st.divider()
    
    # Main content in columns
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Pattern alerts
        st.subheader("🔍 Pattern Detection")
        render_pattern_alerts(patterns)
        
        # Chaos scenarios
        if scenarios:
            render_chaos_scenarios(scenarios)
        
        # Transaction feed
        st.subheader("📜 Live Transactions")
        with st.container(height=400):
            render_transaction_feed(transactions)
    
    with col2:
        # Action history
        st.subheader("⚡ Actions")
        with st.container(height=600):
            render_action_history(actions)
