# ⚡ Vanta

> **Agentic AI for Smart Payment Operations**

A real-time payment operations manager that observes payment behavior, reasons about patterns, decides on interventions, acts with guardrails, and learns from outcomes.

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.31+-red)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 🎯 Problem Statement

Payment failures at scale cause lost revenue, abandoned carts, and broken trust. Traditional systems discover issues after dashboards spike or merchants complain. **Vanta** is a proactive agentic system that:

- **Observes** payment signals in real-time
- **Reasons** about emerging failure patterns
- **Decides** on interventions considering trade-offs
- **Acts** with guardrails and safety constraints
- **Learns** from outcomes to improve future decisions

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           VANTA SYSTEM                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────────┐ │
│  │  OBSERVE │ → │  REASON  │ → │  DECIDE  │ → │      ACT         │ │
│  │          │   │          │   │          │   │                  │ │
│  │ Payment  │   │ Pattern  │   │ Dual-    │   │ Guardrailed     │ │
│  │ Simulator│   │ Detector │   │ Agent    │   │ Executor        │ │
│  │          │   │          │   │ Negoti-  │   │                  │ │
│  │ Bayesian │   │ Hypothesis│   │ ation   │   │ Rollback        │ │
│  │ Router   │   │ Generator│   │          │   │ Support         │ │
│  └──────────┘   └──────────┘   └──────────┘   └──────────────────┘ │
│       │                                              │              │
│       │              ┌──────────────┐                │              │
│       └──────────────│    LEARN     │←───────────────┘              │
│                      │              │                               │
│                      │ Outcome      │                               │
│                      │ Tracker      │                               │
│                      │              │                               │
│                      │ Strategy     │                               │
│                      │ Updater      │                               │
│                      └──────────────┘                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- pip

### Installation

```bash
# Clone the repository
cd "cc 5 v2"

# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run app.py
```

### Access the Dashboard

Open your browser to `http://localhost:8501`

---

## 📁 Project Structure

```
vanta/
├── app.py                    # Main Streamlit application
├── config.py                 # Configuration & constants
├── requirements.txt          # Python dependencies
├── README.md                 # This file
│
├── agents/                   # Dual-agent architecture
│   ├── __init__.py
│   ├── optimizer.py          # Optimizer Agent (success/latency focus)
│   ├── risk_officer.py       # Risk Officer Agent (safety/compliance)
│   └── negotiator.py         # Negotiation Engine
│
├── core/                     # Core engine components
│   ├── __init__.py
│   ├── simulator.py          # Payment simulation with chaos
│   ├── pattern_detector.py   # Statistical pattern detection
│   ├── bayesian_router.py    # Thompson Sampling router
│   ├── action_executor.py    # Guardrailed action execution
│   └── learning_engine.py    # Outcome tracking & adaptation
│
├── models/                   # Data models
│   ├── __init__.py
│   ├── transaction.py        # Transaction & route models
│   └── hypothesis.py         # Pattern, hypothesis, action models
│
└── ui/                       # Streamlit UI components
    ├── __init__.py
    ├── dashboard.py          # Main dashboard
    ├── agent_panel.py        # Agent decision visualization
    └── metrics.py            # Charts and metrics
```

---

## 🔧 Key Components

### 1. Payment Simulator (OBSERVE)
Generates realistic payment streams with chaos scenarios:
- **Issuer Degradation**: Bank-specific performance drops
- **Retry Storms**: Excessive retry patterns
- **Method Fatigue**: Declining payment method performance
- **Latency Spikes**: Gateway response time anomalies

### 2. Pattern Detector (REASON)
Uses statistical methods to identify anomalies:
- Rolling window analysis with z-scores
- Trend detection for method fatigue
- Error clustering analysis
- Hypothesis generation with confidence scoring

### 3. Bayesian Router (DECIDE)
Thompson Sampling for optimal route selection:
- Multi-armed bandit approach
- Balances exploration vs exploitation
- Multi-factor optimization (success, latency, cost)

### 4. Dual-Agent Architecture (DECIDE)

| Agent | Focus | Risk Tolerance |
|-------|-------|----------------|
| **Optimizer** 🚀 | Maximize success rate, minimize latency | Higher |
| **Risk Officer** 🛡️ | Prevent failures, ensure compliance | Lower |

Agents negotiate to reach consensus on actions.

### 5. Action Executor (ACT)
Guardrailed execution with safety constraints:
- Autonomy levels (autonomous, semi-autonomous, manual)
- Rate limiting (max 3 actions per 5 minutes)
- Automatic rollback on failure detection
- Full audit trail

### 6. Learning Engine (LEARN)
Continuous improvement from outcomes:
- Outcome tracking and evaluation
- Hypothesis validation
- Adaptive strategy updates
- Action type effectiveness tracking

---

## 🎮 Demo Features

1. **Start Simulation**: Click "▶️ Start" to begin generating payment traffic
2. **Inject Chaos**: Select a scenario and click "🔥 Inject Chaos"
3. **Watch Patterns**: See real-time pattern detection
4. **Agent Decisions**: View agent negotiations and actions
5. **Analytics**: Explore performance charts and metrics
6. **Learning**: Track how the system improves over time

---

## 🛡️ Ethical & Operational Boundaries

| Boundary | Specification |
|----------|---------------|
| **Autonomous changes** | Retry timing, routing < 20%, method suggestions |
| **Human approval required** | Route > 20% traffic, suppress paths, major config |
| **Detection of incorrect decisions** | Success rate drop > 5%, latency spike > 2x |
| **Rollback mechanism** | Automatic within 60 seconds of detection |
| **Audit trail** | Full logging of all decisions, actions, and outcomes |

---

## 📊 Key Metrics

- **Success Rate**: Target 95%+
- **Avg Latency**: Target < 1500ms
- **Retry Rate**: Target < 10%
- **Agent Consensus Rate**: Tracked in negotiations
- **Hypothesis Accuracy**: Validated over time

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🙏 Acknowledgments

Built for the Agentic AI for Smart Payment Operations challenge.

**Team Vanta** ⚡
