"""
Antigravity Configuration
========================
Central configuration for the Agentic AI Payment Operations system.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List

# =============================================================================
# ENUMS
# =============================================================================

class PaymentMethod(Enum):
    CARD = "card"
    UPI = "upi"
    WALLET = "wallet"
    NETBANKING = "netbanking"

class TransactionStatus(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    PENDING = "pending"

class PatternType(Enum):
    ISSUER_DEGRADATION = "issuer_degradation"
    RETRY_STORM = "retry_storm"
    METHOD_FATIGUE = "method_fatigue"
    LATENCY_SPIKE = "latency_spike"
    ERROR_CLUSTERING = "error_clustering"
    GEOGRAPHIC_ANOMALY = "geographic_anomaly"
    PEAK_HOUR_FAILURE = "peak_hour_failure"

class ActionType(Enum):
    ADJUST_RETRY_STRATEGY = "adjust_retry_strategy"
    REROUTE_TRAFFIC = "reroute_traffic"
    SUPPRESS_PATH = "suppress_path"
    CIRCUIT_BREAK = "circuit_break"
    RECOMMEND_METHOD = "recommend_method"
    ALERT_OPS = "alert_ops"

class AutonomyLevel(Enum):
    AUTONOMOUS = "autonomous"          # No human needed
    SEMI_AUTONOMOUS = "semi_autonomous"  # Alert + confirm within time window
    MANUAL = "manual"                  # Requires explicit approval

class AgentRole(Enum):
    OPTIMIZER = "optimizer"
    RISK_OFFICER = "risk_officer"

# =============================================================================
# SIMULATION CONFIGURATION
# =============================================================================

@dataclass
class SimulationConfig:
    """Configuration for the payment simulation engine."""
    transactions_per_second: float = 10.0
    chaos_probability: float = 0.08  # Reduced from 0.15 for better demo
    chaos_level: float = 0.5  # 0.0-1.0 multiplier for chaos effects
    
    # Banks/Issuers
    banks: List[str] = None
    
    # Base success rates by method (improved for demo)
    base_success_rates: Dict[str, float] = None
    
    # Base latency (ms) by method (reduced for demo)
    base_latency: Dict[str, tuple] = None  # (mean, std)
    
    # Error codes with weights
    error_codes: Dict[str, float] = None
    
    # Provider fees for cost arbitrage
    provider_fees: Dict[str, float] = None
    
    def __post_init__(self):
        if self.banks is None:
            self.banks = [
                "HDFC", "ICICI", "SBI", "AXIS", "KOTAK",
                "PNB", "BOB", "IDBI", "YES", "INDUSIND"
            ]
        
        if self.base_success_rates is None:
            self.base_success_rates = {
                PaymentMethod.CARD.value: 0.96,
                PaymentMethod.UPI.value: 0.98,
                PaymentMethod.WALLET.value: 0.99,
                PaymentMethod.NETBANKING.value: 0.94
            }
        
        if self.base_latency is None:
            self.base_latency = {
                PaymentMethod.CARD.value: (400, 100),
                PaymentMethod.UPI.value: (200, 50),
                PaymentMethod.WALLET.value: (150, 40),
                PaymentMethod.NETBANKING.value: (600, 150)
            }
        
        if self.provider_fees is None:
            self.provider_fees = {
                "razorpay": 0.020,
                "paytm": 0.018,
                "phonepe": 0.015,
                "billdesk": 0.010,
                "ccavenue": 0.025,
            }
        
        if self.error_codes is None:
            self.error_codes = {
                "E001_INSUFFICIENT_FUNDS": 0.15,
                "E002_CARD_EXPIRED": 0.05,
                "E003_INVALID_CVV": 0.03,
                "E004_BANK_DECLINED": 0.12,
                "E005_NETWORK_ERROR": 0.08,
                "E006_TIMEOUT": 0.10,
                "E007_ISSUER_UNAVAILABLE": 0.08,
                "E008_FRAUD_SUSPECTED": 0.04,
                "E009_LIMIT_EXCEEDED": 0.06,
                "E010_INVALID_OTP": 0.07,
                "E011_SESSION_EXPIRED": 0.05,
                "E012_DUPLICATE_TXN": 0.02,
                "E013_BANK_THROTTLING": 0.06,
                "E014_GATEWAY_ERROR": 0.04,
                "E015_3DS_FAILURE": 0.05
            }

# =============================================================================
# PATTERN DETECTION CONFIGURATION
# =============================================================================

@dataclass
class PatternConfig:
    """Configuration for pattern detection thresholds."""
    # Rolling window sizes
    short_window: int = 30      # 30 seconds
    medium_window: int = 300    # 5 minutes
    long_window: int = 1800     # 30 minutes
    
    # Z-score thresholds for anomaly detection
    issuer_degradation_zscore: float = 2.0
    latency_spike_zscore: float = 2.5
    
    # Retry storm thresholds
    retry_ratio_threshold: float = 0.3  # 30% retries = storm
    retry_storm_window: int = 60        # 1 minute window
    
    # Method fatigue
    method_fatigue_drop: float = 0.10   # 10% drop from baseline
    
    # Error clustering
    error_cluster_threshold: float = 0.25  # 25% of errors same type
    
    # Minimum sample size for statistical significance
    min_sample_size: int = 20

# =============================================================================
# AGENT CONFIGURATION
# =============================================================================

@dataclass
class OptimizerConfig:
    """Configuration for the Optimizer Agent."""
    # Optimization weights
    success_weight: float = 0.5
    latency_weight: float = 0.3
    cost_weight: float = 0.2
    
    # Exploration factor for Thompson Sampling
    exploration_bonus: float = 0.1
    
    # Action preferences
    max_traffic_shift_autonomous: float = 0.20  # 20%
    preferred_retry_delays: List[int] = None   # ms
    
    def __post_init__(self):
        if self.preferred_retry_delays is None:
            self.preferred_retry_delays = [1000, 2000, 4000, 8000]  # Exponential backoff

@dataclass
class RiskOfficerConfig:
    """Configuration for the Risk Officer Agent."""
    # Hard limits
    max_retry_count: int = 3
    max_cost_per_txn: float = 5.0  # rupees
    fraud_score_threshold: float = 0.7
    
    # Rate limiting
    max_actions_per_window: int = 3
    action_window_seconds: int = 300  # 5 minutes
    
    # Rollback triggers
    success_rate_drop_trigger: float = 0.05  # 5% drop
    latency_spike_trigger: float = 2.0       # 2x increase
    
    # Veto thresholds
    traffic_shift_veto_threshold: float = 0.30  # Veto if > 30%
    
    # Monitoring window after action
    post_action_monitoring_seconds: int = 60

# =============================================================================
# ACTION EXECUTOR CONFIGURATION
# =============================================================================

@dataclass
class ExecutorConfig:
    """Configuration for action execution and guardrails."""
    # Autonomy mappings
    autonomy_levels: Dict[str, str] = None
    
    # Rollback settings
    rollback_window_seconds: int = 60
    auto_rollback_on_failure: bool = True
    
    # Logging
    log_all_actions: bool = True
    
    def __post_init__(self):
        if self.autonomy_levels is None:
            self.autonomy_levels = {
                ActionType.ADJUST_RETRY_STRATEGY.value: AutonomyLevel.AUTONOMOUS.value,
                ActionType.REROUTE_TRAFFIC.value: AutonomyLevel.SEMI_AUTONOMOUS.value,
                ActionType.SUPPRESS_PATH.value: AutonomyLevel.SEMI_AUTONOMOUS.value,
                ActionType.CIRCUIT_BREAK.value: AutonomyLevel.AUTONOMOUS.value,
                ActionType.RECOMMEND_METHOD.value: AutonomyLevel.AUTONOMOUS.value,
                ActionType.ALERT_OPS.value: AutonomyLevel.AUTONOMOUS.value,
            }

# =============================================================================
# LEARNING ENGINE CONFIGURATION
# =============================================================================

@dataclass
class LearningConfig:
    """Configuration for the learning loop."""
    # Outcome evaluation windows
    immediate_window: int = 30    # 30 seconds
    short_term_window: int = 300  # 5 minutes
    long_term_window: int = 3600  # 1 hour
    
    # Bayesian prior updates
    prior_weight: float = 0.3     # Weight given to prior vs new evidence
    
    # Hypothesis validation
    min_confidence_to_act: float = 0.6
    hypothesis_expiry_seconds: int = 600  # 10 minutes
    
    # Strategy adaptation
    adaptation_rate: float = 0.1  # Learning rate for strategy updates

# =============================================================================
# UI CONFIGURATION
# =============================================================================

@dataclass
class UIConfig:
    """Configuration for the Streamlit UI."""
    refresh_interval_ms: int = 1000
    max_transactions_display: int = 100
    max_actions_history: int = 50
    chart_height: int = 300
    
    # Color scheme
    colors: Dict[str, str] = None
    
    def __post_init__(self):
        if self.colors is None:
            self.colors = {
                "success": "#10B981",
                "failure": "#EF4444",
                "warning": "#F59E0B",
                "info": "#3B82F6",
                "primary": "#8B5CF6",
                "secondary": "#6366F1",
                "background": "#0F172A",
                "surface": "#1E293B",
                "text": "#F1F5F9"
            }

# =============================================================================
# GLOBAL CONFIGURATION INSTANCE
# =============================================================================

class Config:
    """Global configuration container."""
    simulation = SimulationConfig()
    patterns = PatternConfig()
    optimizer = OptimizerConfig()
    risk_officer = RiskOfficerConfig()
    executor = ExecutorConfig()
    learning = LearningConfig()
    ui = UIConfig()

# Export singleton
config = Config()
