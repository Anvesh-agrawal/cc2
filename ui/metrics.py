"""
Metrics Components
==================
Performance metrics and chart visualizations.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any

from config import config


def render_metrics(
    current_metrics: Dict[str, float],
    historical_metrics: List[Dict] = None
):
    """Render key performance metrics."""
    
    cols = st.columns(4)
    
    metrics_config = [
        ("Success Rate", "success_rate", "{:.1%}", 0.95, "higher"),
        ("Avg Latency", "avg_latency", "{:.0f}ms", 1500, "lower"),
        ("Retry Rate", "retry_rate", "{:.1%}", 0.1, "lower"),
        ("Error Rate", "error_rate", "{:.1%}", 0.05, "lower")
    ]
    
    for i, (label, key, fmt, target, direction) in enumerate(metrics_config):
        with cols[i]:
            value = current_metrics.get(key, 0)
            
            # Calculate delta if we have history
            delta = None
            if historical_metrics and len(historical_metrics) > 1:
                prev_value = historical_metrics[-2].get(key, value)
                delta = value - prev_value
            
            # Format the value
            if "%" in fmt:
                display_value = fmt.format(value)
            else:
                display_value = fmt.format(value)
            
            # Determine if the delta is good or bad
            if delta is not None:
                if direction == "higher":
                    delta_color = "normal" if delta >= 0 else "inverse"
                else:
                    delta_color = "normal" if delta <= 0 else "inverse"
                
                delta_str = f"{delta:+.2%}" if "%" in fmt else f"{delta:+.0f}"
                st.metric(label, display_value, delta_str, delta_color=delta_color)
            else:
                st.metric(label, display_value)


def render_success_rate_chart(historical_data: List[Dict], height: int = 300):
    """Render success rate time series chart."""
    
    if not historical_data:
        st.caption("No historical data available")
        return
    
    df = pd.DataFrame(historical_data)
    
    if "timestamp" not in df.columns:
        df["timestamp"] = pd.date_range(end=datetime.now(), periods=len(df), freq="s")
    
    fig = go.Figure()
    
    # Success rate line
    fig.add_trace(go.Scatter(
        x=df["timestamp"],
        y=df.get("success_rate", [0.9] * len(df)),
        name="Success Rate",
        line=dict(color="#10B981", width=2),
        fill="tozeroy",
        fillcolor="rgba(16, 185, 129, 0.1)"
    ))
    
    # Target line
    fig.add_hline(y=0.95, line_dash="dash", line_color="#F59E0B", 
                  annotation_text="Target 95%", annotation_position="right")
    
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=30, b=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, color="#94A3B8"),
        yaxis=dict(
            showgrid=True, 
            gridcolor="#334155",
            color="#94A3B8",
            tickformat=".0%",
            range=[0.7, 1.0]
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color="#94A3B8")
        ),
        title=dict(text="Success Rate Over Time", font=dict(color="#E2E8F0", size=14))
    )
    
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_latency_distribution(transactions: List[Dict], height: int = 250):
    """Render latency distribution histogram."""
    
    if not transactions:
        st.caption("No transaction data available")
        return
    
    latencies = [t.get("latency_ms", 0) for t in transactions]
    
    fig = go.Figure()
    
    fig.add_trace(go.Histogram(
        x=latencies,
        nbinsx=30,
        marker_color="#8B5CF6",
        opacity=0.7,
        name="Latency"
    ))
    
    # Add percentile lines
    if latencies:
        p50 = sorted(latencies)[len(latencies) // 2]
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        
        fig.add_vline(x=p50, line_dash="dash", line_color="#10B981",
                      annotation_text=f"P50: {p50:.0f}ms")
        fig.add_vline(x=p95, line_dash="dash", line_color="#F59E0B",
                      annotation_text=f"P95: {p95:.0f}ms")
    
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=30, b=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            title="Latency (ms)",
            showgrid=False,
            color="#94A3B8"
        ),
        yaxis=dict(
            title="Count",
            showgrid=True,
            gridcolor="#334155",
            color="#94A3B8"
        ),
        title=dict(text="Latency Distribution", font=dict(color="#E2E8F0", size=14))
    )
    
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_bank_performance(bank_stats: Dict[str, Dict], height: int = 300):
    """Render bank performance comparison chart."""
    
    if not bank_stats:
        st.caption("No bank data available")
        return
    
    banks = list(bank_stats.keys())
    success_rates = [bank_stats[b].get("success_rate", 0) for b in banks]
    totals = [bank_stats[b].get("total", 0) for b in banks]
    
    # Colors based on performance
    colors = [
        "#10B981" if sr >= 0.9 else "#F59E0B" if sr >= 0.8 else "#EF4444"
        for sr in success_rates
    ]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=banks,
        y=success_rates,
        marker_color=colors,
        text=[f"{sr:.1%}" for sr in success_rates],
        textposition="outside",
        name="Success Rate"
    ))
    
    # Add transaction count as secondary info
    fig.add_trace(go.Scatter(
        x=banks,
        y=[0.5] * len(banks),  # Invisible line
        mode="text",
        text=[f"n={t}" for t in totals],
        textposition="bottom center",
        textfont=dict(color="#94A3B8", size=10),
        showlegend=False
    ))
    
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=30, b=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, color="#94A3B8"),
        yaxis=dict(
            showgrid=True,
            gridcolor="#334155",
            color="#94A3B8",
            tickformat=".0%",
            range=[0, 1.1]
        ),
        title=dict(text="Bank Performance", font=dict(color="#E2E8F0", size=14)),
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_method_performance(method_stats: Dict[str, Dict], height: int = 250):
    """Render payment method performance chart."""
    
    if not method_stats:
        st.caption("No method data available")
        return
    
    methods = list(method_stats.keys())
    success_rates = [method_stats[m].get("success_rate", 0) for m in methods]
    latencies = [method_stats[m].get("avg_latency", 0) for m in methods]
    totals = [method_stats[m].get("total", 0) for m in methods]
    
    # Create subplot with two y-axes
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Success rate bars
    fig.add_trace(
        go.Bar(
            x=methods,
            y=success_rates,
            name="Success Rate",
            marker_color="#8B5CF6",
            opacity=0.8
        ),
        secondary_y=False
    )
    
    # Latency line
    fig.add_trace(
        go.Scatter(
            x=methods,
            y=latencies,
            name="Avg Latency",
            mode="lines+markers",
            line=dict(color="#F59E0B", width=2),
            marker=dict(size=8)
        ),
        secondary_y=True
    )
    
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=30, b=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color="#94A3B8")
        ),
        title=dict(text="Payment Method Performance", font=dict(color="#E2E8F0", size=14))
    )
    
    fig.update_xaxes(showgrid=False, color="#94A3B8")
    fig.update_yaxes(
        title_text="Success Rate",
        tickformat=".0%",
        showgrid=True,
        gridcolor="#334155",
        color="#94A3B8",
        secondary_y=False
    )
    fig.update_yaxes(
        title_text="Latency (ms)",
        showgrid=False,
        color="#94A3B8",
        secondary_y=True
    )
    
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_error_distribution(error_data: Dict[str, int], height: int = 250):
    """Render error code distribution pie chart."""
    
    if not error_data:
        st.caption("No error data available")
        return
    
    # Sort by count and take top 8
    sorted_errors = sorted(error_data.items(), key=lambda x: x[1], reverse=True)[:8]
    labels = [e[0].replace("_", " ") for e in sorted_errors]
    values = [e[1] for e in sorted_errors]
    
    fig = go.Figure()
    
    fig.add_trace(go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker=dict(
            colors=px.colors.sequential.Plasma[:len(labels)]
        ),
        textinfo="percent+label",
        textposition="outside",
        textfont=dict(size=10, color="#E2E8F0")
    ))
    
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=30, b=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        title=dict(text="Error Distribution", font=dict(color="#E2E8F0", size=14))
    )
    
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_route_heatmap(route_data: List[Dict], height: int = 400):
    """Render route performance heatmap."""
    
    if not route_data:
        st.caption("No route data available")
        return
    
    # Prepare data for heatmap
    banks = list(set(r["bank"] for r in route_data))
    methods = list(set(r["payment_method"] for r in route_data))
    
    # Create matrix
    matrix = []
    for bank in banks:
        row = []
        for method in methods:
            route = next(
                (r for r in route_data if r["bank"] == bank and r["payment_method"] == method),
                None
            )
            row.append(route["success_rate"] if route else None)
        matrix.append(row)
    
    fig = go.Figure()
    
    fig.add_trace(go.Heatmap(
        z=matrix,
        x=methods,
        y=banks,
        colorscale=[
            [0, "#EF4444"],
            [0.5, "#F59E0B"],
            [1, "#10B981"]
        ],
        zmin=0.7,
        zmax=1.0,
        text=[[f"{v:.1%}" if v else "" for v in row] for row in matrix],
        texttemplate="%{text}",
        textfont=dict(size=10, color="white"),
        hovertemplate="Bank: %{y}<br>Method: %{x}<br>Success: %{z:.1%}<extra></extra>"
    ))
    
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=30, b=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(color="#94A3B8"),
        yaxis=dict(color="#94A3B8"),
        title=dict(text="Route Performance Heatmap", font=dict(color="#E2E8F0", size=14))
    )
    
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_charts(
    historical_data: List[Dict],
    transactions: List[Dict],
    bank_stats: Dict,
    method_stats: Dict,
    error_data: Dict,
    route_data: List[Dict]
):
    """Render all charts in a grid layout."""
    
    tabs = st.tabs(["📈 Trends", "🏦 Banks", "💳 Methods", "🗺️ Routes", "🧠 Learning"])
    
    with tabs[0]:
        render_success_rate_chart(historical_data)
        render_latency_distribution(transactions)
    
    with tabs[1]:
        render_bank_performance(bank_stats)
        render_error_distribution(error_data)
    
    with tabs[2]:
        render_method_performance(method_stats)
    
    with tabs[3]:
        render_route_heatmap(route_data)
    
    with tabs[4]:
        render_learning_trajectory(historical_data)
        render_provider_leaderboard(route_data)
        render_beta_distributions(route_data)


def render_learning_trajectory(historical_data: List[Dict], height: int = 300):
    """Render learning trajectory showing improvement over time."""
    
    if not historical_data or len(historical_data) < 5:
        st.caption("⏳ Collecting data to show learning trajectory...")
        return
    
    df = pd.DataFrame(historical_data)
    
    if "timestamp" not in df.columns:
        df["timestamp"] = pd.date_range(end=datetime.now(), periods=len(df), freq="s")
    
    # Calculate rolling average to show learning
    df["success_rate_smooth"] = df.get("success_rate", pd.Series([0.9] * len(df))).rolling(window=5, min_periods=1).mean()
    
    # Calculate improvement delta from start
    start_rate = df["success_rate_smooth"].iloc[0] if len(df) > 0 else 0.9
    current_rate = df["success_rate_smooth"].iloc[-1] if len(df) > 0 else 0.9
    improvement = current_rate - start_rate
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Starting Rate", f"{start_rate:.1%}")
    with col2:
        st.metric("Current Rate", f"{current_rate:.1%}")
    with col3:
        st.metric("Improvement", f"{improvement:+.1%}", delta=f"{improvement*100:+.1f}pp")
    
    fig = go.Figure()
    
    # Raw data
    fig.add_trace(go.Scatter(
        x=df["timestamp"],
        y=df.get("success_rate", [0.9] * len(df)),
        name="Raw",
        line=dict(color="#6366F1", width=1),
        opacity=0.3
    ))
    
    # Smoothed learning curve
    fig.add_trace(go.Scatter(
        x=df["timestamp"],
        y=df["success_rate_smooth"],
        name="Learning Curve",
        line=dict(color="#10B981", width=3),
        fill="tozeroy",
        fillcolor="rgba(16, 185, 129, 0.1)"
    ))
    
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=30, b=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, color="#94A3B8"),
        yaxis=dict(
            showgrid=True,
            gridcolor="#334155",
            color="#94A3B8",
            tickformat=".0%",
            range=[0.7, 1.0]
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color="#94A3B8")
        ),
        title=dict(text="📈 Agent Learning Trajectory", font=dict(color="#E2E8F0", size=14))
    )
    
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_provider_leaderboard(route_data: List[Dict]):
    """Render provider performance leaderboard."""
    
    if not route_data:
        st.caption("No provider data available")
        return
    
    st.subheader("🏆 Provider Leaderboard")
    
    # Aggregate by gateway
    from collections import defaultdict
    gateway_stats = defaultdict(lambda: {"success": 0, "total": 0, "latency_sum": 0, "fee": 0})
    
    for route in route_data:
        gateway = route.get("gateway", "unknown")
        gateway_stats[gateway]["success"] += route.get("successful_transactions", 0)
        gateway_stats[gateway]["total"] += route.get("total_transactions", 0)
        gateway_stats[gateway]["latency_sum"] += route.get("avg_latency", 0) * route.get("total_transactions", 1)
    
    # Provider fees
    provider_fees = {
        "razorpay": 2.0,
        "paytm": 1.8,
        "phonepe": 1.5,
        "billdesk": 1.0,
        "ccavenue": 2.5,
    }
    
    # Calculate metrics and rank
    leaderboard = []
    for gateway, stats in gateway_stats.items():
        if stats["total"] > 0:
            success_rate = stats["success"] / stats["total"]
            avg_latency = stats["latency_sum"] / stats["total"]
            fee = provider_fees.get(gateway, 2.0)
            # EV score (higher is better)
            ev_score = success_rate * (1 - fee/100)
            
            leaderboard.append({
                "Provider": gateway.title(),
                "Success Rate": f"{success_rate:.1%}",
                "Avg Latency": f"{avg_latency:.0f}ms",
                "Fee": f"{fee:.1f}%",
                "EV Score": f"{ev_score:.3f}",
                "_ev": ev_score  # For sorting
            })
    
    # Sort by EV score
    leaderboard.sort(key=lambda x: x["_ev"], reverse=True)
    
    # Add rank
    for i, item in enumerate(leaderboard):
        medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"#{i+1}"
        item["Rank"] = medal
        del item["_ev"]
    
    if leaderboard:
        # Reorder columns
        df = pd.DataFrame(leaderboard)[["Rank", "Provider", "Success Rate", "Avg Latency", "Fee", "EV Score"]]
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.caption("No provider data yet")


def render_beta_distributions(route_data: List[Dict], height: int = 300):
    """Visualize Thompson Sampling Beta distributions for top routes."""
    
    if not route_data:
        st.caption("No route data for Beta visualization")
        return
    
    st.subheader("🎲 Bayesian Confidence (Thompson Sampling)")
    st.caption("Narrower curves = higher confidence. Agent learns which routes work best.")
    
    # Filter to top 5 by transaction count
    sorted_routes = sorted(route_data, key=lambda x: x.get("total_transactions", 0), reverse=True)[:5]
    
    if not sorted_routes:
        st.caption("Insufficient data for visualization")
        return
    
    import numpy as np
    from scipy import stats as scipy_stats
    
    fig = go.Figure()
    
    colors = ["#8B5CF6", "#10B981", "#F59E0B", "#EF4444", "#3B82F6"]
    
    x = np.linspace(0, 1, 200)
    
    for i, route in enumerate(sorted_routes):
        alpha = route.get("alpha", 1.0)
        beta = route.get("beta", 1.0)
        
        # Calculate Beta distribution PDF
        try:
            y = scipy_stats.beta.pdf(x, alpha, beta)
        except:
            continue
        
        route_name = f"{route.get('gateway', 'unknown')}"
        
        fig.add_trace(go.Scatter(
            x=x,
            y=y,
            name=f"{route_name} (α={alpha:.0f}, β={beta:.0f})",
            line=dict(color=colors[i % len(colors)], width=2),
            fill="tozeroy",
            fillcolor=f"rgba{tuple(list(int(colors[i % len(colors)].lstrip('#')[j:j+2], 16) for j in (0, 2, 4)) + [0.1])}"
        ))
    
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=10, b=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            title="Success Probability",
            showgrid=False,
            color="#94A3B8",
            tickformat=".0%"
        ),
        yaxis=dict(
            title="Density",
            showgrid=True,
            gridcolor="#334155",
            color="#94A3B8"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color="#94A3B8", size=10)
        )
    )
    
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
