"""
Agent Panel Components
=====================
UI components for agent decisions and negotiation visualization.
"""

import streamlit as st
from datetime import datetime
from typing import Dict, List, Optional, Any


def render_agent_panel(
    optimizer_stats: Dict,
    risk_officer_stats: Dict,
    negotiation_stats: Dict,
    pending_approvals: List[Dict],
    on_approve: callable = None,
    on_reject: callable = None
):
    """Render the agent decision panel."""
    
    st.subheader("🤖 Agent Decision Center")
    
    # Agent health cards
    col1, col2, col3 = st.columns(3)
    
    with col1:
        _render_agent_card(
            name="Optimizer",
            icon="🚀",
            color="#10B981",
            stats={
                "Decisions": optimizer_stats.get("decisions_made", 0),
                "Health Score": f"{sum(g.get('score', 0) for g in optimizer_stats.get('current_goals', [])) / max(1, len(optimizer_stats.get('current_goals', []))):.0%}"
            }
        )
    
    with col2:
        _render_agent_card(
            name="Risk Officer",
            icon="🛡️",
            color="#F59E0B",
            stats={
                "Vetoes": risk_officer_stats.get("total_vetoes", 0),
                "Veto Rate": f"{risk_officer_stats.get('veto_rate', 0):.0%}",
                "Incidents": risk_officer_stats.get("active_incidents", 0)
            }
        )
    
    with col3:
        _render_agent_card(
            name="Negotiator",
            icon="🤝",
            color="#8B5CF6",
            stats={
                "Negotiations": negotiation_stats.get("total_negotiations", 0),
                "Consensus Rate": f"{negotiation_stats.get('consensus_rate', 0):.0%}",
                "Avg Rounds": f"{negotiation_stats.get('avg_rounds', 0):.1f}"
            }
        )
    
    st.divider()
    
    # Pending approvals
    if pending_approvals:
        st.subheader("⏳ Pending Approvals")
        
        for approval in pending_approvals:
            _render_approval_card(approval, on_approve, on_reject)
    else:
        st.info("✅ No pending approvals")


def _render_agent_card(name: str, icon: str, color: str, stats: Dict):
    """Render an agent status card."""
    
    stats_html = "".join([
        f'<div style="display: flex; justify-content: space-between; margin: 0.25rem 0;">'
        f'<span style="color: #94A3B8;">{k}</span>'
        f'<span style="color: #E2E8F0; font-weight: 600;">{v}</span>'
        f'</div>'
        for k, v in stats.items()
    ])
    
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        border-radius: 1rem;
        padding: 1rem;
        border: 1px solid {color}44;
        border-top: 3px solid {color};
    ">
        <div style="display: flex; align-items: center; margin-bottom: 0.75rem;">
            <span style="font-size: 1.5rem; margin-right: 0.5rem;">{icon}</span>
            <span style="font-size: 1.1rem; font-weight: 600; color: {color};">{name}</span>
        </div>
        {stats_html}
    </div>
    """, unsafe_allow_html=True)


def _render_approval_card(
    approval: Dict,
    on_approve: callable,
    on_reject: callable
):
    """Render a pending approval card."""
    
    action_type = approval.get("action_type", "unknown").replace("_", " ").title()
    risk_score = approval.get("risk_score", 0)
    
    risk_color = "#10B981" if risk_score < 0.3 else "#F59E0B" if risk_score < 0.6 else "#EF4444"
    
    with st.container():
        st.markdown(f"""
        <div style="
            background: #1E293B;
            border-radius: 0.75rem;
            padding: 1rem;
            margin: 0.5rem 0;
            border-left: 4px solid {risk_color};
        ">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: 600; font-size: 1.1rem;">{action_type}</span>
                <span style="
                    background: {risk_color}22;
                    color: {risk_color};
                    padding: 0.25rem 0.75rem;
                    border-radius: 1rem;
                    font-size: 0.8rem;
                    font-weight: 600;
                ">Risk: {risk_score:.0%}</span>
            </div>
            <p style="color: #94A3B8; margin: 0.5rem 0;">
                {approval.get("description", "")}
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Approve", key=f"approve_{approval.get('id')}", use_container_width=True):
                if on_approve:
                    on_approve(approval.get("id"))
        with col2:
            if st.button("❌ Reject", key=f"reject_{approval.get('id')}", use_container_width=True):
                if on_reject:
                    on_reject(approval.get("id"))


def render_negotiation_panel(negotiations: List[Dict]):
    """Render the negotiation history panel."""
    
    st.subheader("🤝 Negotiation History")
    
    if not negotiations:
        st.info("No negotiations yet")
        return
    
    for neg in negotiations[:5]:
        _render_negotiation_card(neg)


def _render_negotiation_card(negotiation: Dict):
    """Render a negotiation record card."""
    
    consensus = negotiation.get("consensus_reached", False)
    decision = negotiation.get("final_decision", "pending")
    rounds = negotiation.get("rounds_count", 0)
    
    decision_colors = {
        "approved": "#10B981",
        "modified": "#F59E0B",
        "rejected": "#EF4444",
        "pending": "#6B7280"
    }
    color = decision_colors.get(decision, "#6B7280")
    
    with st.expander(
        f"{'✅' if consensus else '❌'} {negotiation.get('original_action_type', 'Unknown').replace('_', ' ').title()} → {decision.upper()}",
        expanded=False
    ):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Rounds", rounds)
        with col2:
            st.metric("Consensus", "Yes" if consensus else "No")
        with col3:
            st.metric("Decision", decision.title())
        
        st.divider()
        
        # Reasoning
        if negotiation.get("optimizer_reasoning"):
            st.markdown("**Optimizer Reasoning:**")
            st.caption(negotiation.get("optimizer_reasoning", "")[:300] + "...")
        
        if negotiation.get("risk_officer_reasoning"):
            st.markdown("**Risk Officer Reasoning:**")
            st.caption(negotiation.get("risk_officer_reasoning", "")[:300] + "...")
        
        if negotiation.get("compromise_details"):
            st.markdown("**Compromise:**")
            st.info(negotiation.get("compromise_details"))


def render_agent_reasoning(
    agent_name: str,
    reasoning: str,
    icon: str = "🤖",
    color: str = "#8B5CF6"
):
    """Render agent reasoning in a styled box."""
    
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, {color}11 0%, {color}05 100%);
        border-radius: 0.75rem;
        padding: 1rem;
        border-left: 3px solid {color};
        margin: 0.5rem 0;
    ">
        <div style="display: flex; align-items: center; margin-bottom: 0.5rem;">
            <span style="font-size: 1.25rem; margin-right: 0.5rem;">{icon}</span>
            <span style="font-weight: 600; color: {color};">{agent_name}</span>
        </div>
        <div style="color: #E2E8F0; font-size: 0.9rem; white-space: pre-wrap;">
            {reasoning}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_decision_flow(
    pattern: Dict,
    hypothesis: Dict,
    action: Dict,
    negotiation: Dict = None
):
    """Render the decision flow visualization."""
    
    st.subheader("🔄 Decision Flow")
    
    # Pattern → Hypothesis → Action → Negotiation
    cols = st.columns(4)
    
    with cols[0]:
        st.markdown("**🔍 Pattern**")
        st.caption(pattern.get("pattern_type", "").replace("_", " ").title())
        st.caption(f"Entity: {pattern.get('affected_entity', '')}")
        st.caption(f"Confidence: {pattern.get('confidence', 0):.0%}")
    
    with cols[1]:
        st.markdown("**💡 Hypothesis**")
        st.caption(hypothesis.get("description", "")[:100] + "...")
        st.caption(f"Root Cause: {hypothesis.get('root_cause', '')[:50]}...")
    
    with cols[2]:
        st.markdown("**⚡ Action**")
        st.caption(action.get("action_type", "").replace("_", " ").title())
        st.caption(f"Risk: {action.get('risk_score', 0):.0%}")
        st.caption(f"Expected Δ: {action.get('expected_success_rate_delta', 0):.1%}")
    
    with cols[3]:
        if negotiation:
            st.markdown("**🤝 Negotiation**")
            st.caption(f"Decision: {negotiation.get('final_decision', 'pending').title()}")
            st.caption(f"Rounds: {negotiation.get('rounds_count', 0)}")
        else:
            st.markdown("**⏳ Pending**")
            st.caption("Awaiting negotiation...")


def render_learning_insights(learnings: List[Dict], action_stats: Dict):
    """Render learning insights panel."""
    
    st.subheader("🧠 Learning Insights")
    
    # Action type effectiveness
    if action_stats:
        st.markdown("**Action Type Effectiveness**")
        
        for action_type, stats in action_stats.items():
            success_rate = stats.get("success_rate", 0)
            total = stats.get("total", 0)
            avg_improvement = stats.get("avg_improvement", 0)
            
            if total > 0:
                color = "#10B981" if success_rate >= 0.7 else "#F59E0B" if success_rate >= 0.5 else "#EF4444"
                
                st.markdown(f"""
                <div style="
                    display: flex;
                    align-items: center;
                    padding: 0.5rem;
                    margin: 0.25rem 0;
                    background: {color}11;
                    border-radius: 0.5rem;
                ">
                    <span style="min-width: 150px; font-weight: 500;">{action_type.replace('_', ' ').title()}</span>
                    <span style="color: {color}; min-width: 80px;">{success_rate:.0%} success</span>
                    <span style="color: #94A3B8; min-width: 60px;">{total} uses</span>
                    <span style="color: {'#10B981' if avg_improvement > 0 else '#EF4444'}; margin-left: auto;">
                        {'+' if avg_improvement > 0 else ''}{avg_improvement:.1%} avg
                    </span>
                </div>
                """, unsafe_allow_html=True)
    
    # Recent learnings
    if learnings:
        st.markdown("**Recent Learnings**")
        
        for learning in learnings[:5]:
            event_type = learning.get("event_type", "")
            is_positive = "positive" in event_type or "validated" in event_type
            
            icon = "✅" if is_positive else "❌" if "negative" in event_type else "ℹ️"
            color = "#10B981" if is_positive else "#EF4444" if "negative" in event_type else "#6B7280"
            
            st.markdown(f"""
            <div style="
                padding: 0.5rem;
                margin: 0.25rem 0;
                border-left: 3px solid {color};
                padding-left: 0.75rem;
            ">
                <span>{icon}</span>
                <span style="color: #E2E8F0; font-size: 0.9rem;">{learning.get('learning', '')}</span>
            </div>
            """, unsafe_allow_html=True)
