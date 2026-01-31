"""
Pattern Detector
================
Statistical pattern detection using rolling windows, z-scores, and trend analysis.
"""

import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass, field
import statistics

from config import PatternType, PatternConfig, config
from models.transaction import Transaction, TransactionBatch
from models.hypothesis import Pattern, Hypothesis


@dataclass
class RollingStats:
    """Maintains rolling statistics for a metric."""
    window_size: int = 60  # seconds
    values: List[Tuple[datetime, float]] = field(default_factory=list)
    
    def add(self, value: float, timestamp: datetime = None):
        """Add a new value to the rolling window."""
        ts = timestamp or datetime.now()
        self.values.append((ts, value))
        self._cleanup(ts)
    
    def _cleanup(self, current_time: datetime):
        """Remove values outside the window."""
        cutoff = current_time - timedelta(seconds=self.window_size)
        self.values = [(ts, v) for ts, v in self.values if ts > cutoff]
    
    @property
    def count(self) -> int:
        return len(self.values)
    
    @property
    def mean(self) -> float:
        if not self.values:
            return 0.0
        return statistics.mean(v for _, v in self.values)
    
    @property
    def std(self) -> float:
        if len(self.values) < 2:
            return 0.0
        return statistics.stdev(v for _, v in self.values)
    
    @property
    def latest(self) -> Optional[float]:
        if not self.values:
            return None
        return self.values[-1][1]
    
    def get_z_score(self, value: float) -> float:
        """Calculate z-score for a value."""
        if self.std == 0:
            return 0.0
        return (value - self.mean) / self.std
    
    def get_percentile(self, p: float) -> float:
        """Get the p-th percentile of values."""
        if not self.values:
            return 0.0
        sorted_values = sorted(v for _, v in self.values)
        idx = int(len(sorted_values) * p / 100)
        return sorted_values[min(idx, len(sorted_values) - 1)]


class PatternDetector:
    """
    Detects patterns in payment data streams using statistical methods.
    
    Patterns detected:
    - Issuer degradation (success rate drop by bank)
    - Retry storms (high retry ratio)
    - Method fatigue (declining method performance)
    - Latency spikes (percentile drift)
    - Error clustering (specific error dominance)
    """
    
    def __init__(self, config: PatternConfig = None):
        self.config = config or PatternConfig()
        
        # Rolling stats by entity
        self.bank_success_rates: Dict[str, RollingStats] = defaultdict(
            lambda: RollingStats(window_size=self.config.medium_window)
        )
        self.method_success_rates: Dict[str, RollingStats] = defaultdict(
            lambda: RollingStats(window_size=self.config.medium_window)
        )
        self.gateway_latencies: Dict[str, RollingStats] = defaultdict(
            lambda: RollingStats(window_size=self.config.short_window)
        )
        
        # Global stats
        self.global_success_rate = RollingStats(window_size=self.config.long_window)
        self.retry_tracker = RollingStats(window_size=self.config.retry_storm_window)
        
        # Error tracking
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.error_window_start = datetime.now()
        
        # Baseline metrics (learned over time)
        self.baselines: Dict[str, float] = {}
        
        # Detected patterns
        self.active_patterns: List[Pattern] = []
        self.pattern_history: List[Pattern] = []
        
        # Hypotheses
        self.active_hypotheses: List[Hypothesis] = []
    
    def process_transaction(self, txn: Transaction) -> List[Pattern]:
        """Process a transaction and detect any patterns."""
        now = datetime.now()
        
        # Update rolling stats
        success_val = 1.0 if txn.is_successful else 0.0
        
        self.bank_success_rates[txn.issuer_bank].add(success_val, now)
        self.method_success_rates[txn.payment_method.value].add(success_val, now)
        self.gateway_latencies[txn.gateway].add(txn.latency_ms, now)
        self.global_success_rate.add(success_val, now)
        
        # Track retries
        self.retry_tracker.add(1.0 if txn.is_retry else 0.0, now)
        
        # Track errors
        if txn.error_code:
            self._update_error_counts(txn.error_code)
        
        # Detect patterns
        new_patterns = self._detect_patterns(txn)
        
        # Generate hypotheses for new patterns
        for pattern in new_patterns:
            hypothesis = self._generate_hypothesis(pattern)
            if hypothesis:
                self.active_hypotheses.append(hypothesis)
        
        return new_patterns
    
    def process_batch(self, batch: TransactionBatch) -> List[Pattern]:
        """Process a batch of transactions."""
        all_patterns = []
        for txn in batch.transactions:
            patterns = self.process_transaction(txn)
            all_patterns.extend(patterns)
        return all_patterns
    
    def _detect_patterns(self, txn: Transaction) -> List[Pattern]:
        """Run all pattern detection algorithms."""
        patterns = []
        
        # Check each detection algorithm
        pattern = self._detect_issuer_degradation(txn.issuer_bank)
        if pattern:
            patterns.append(pattern)
        
        pattern = self._detect_retry_storm()
        if pattern:
            patterns.append(pattern)
        
        pattern = self._detect_method_fatigue(txn.payment_method.value)
        if pattern:
            patterns.append(pattern)
        
        pattern = self._detect_latency_spike(txn.gateway)
        if pattern:
            patterns.append(pattern)
        
        pattern = self._detect_error_clustering()
        if pattern:
            patterns.append(pattern)
        
        # Add new patterns, avoiding duplicates
        for p in patterns:
            if not self._is_duplicate_pattern(p):
                self.active_patterns.append(p)
                self.pattern_history.append(p)
        
        # Clean up old patterns
        self._cleanup_old_patterns()
        
        return patterns
    
    def _detect_issuer_degradation(self, bank: str) -> Optional[Pattern]:
        """Detect issuer-specific degradation."""
        stats = self.bank_success_rates[bank]
        
        if stats.count < self.config.min_sample_size:
            return None
        
        # Get baseline (use global if no specific baseline)
        baseline_key = f"bank_{bank}_success"
        baseline = self.baselines.get(baseline_key, 0.92)
        
        current_rate = stats.mean
        
        # Calculate z-score against baseline
        # Use a synthetic std if we don't have enough history
        expected_std = 0.05  # Expected variation
        z_score = (baseline - current_rate) / expected_std if expected_std > 0 else 0
        
        if z_score >= self.config.issuer_degradation_zscore:
            severity = min(1.0, z_score / 5.0)  # Normalize severity
            confidence = min(0.95, 0.5 + stats.count / 100)  # More samples = more confidence
            
            return Pattern(
                pattern_type=PatternType.ISSUER_DEGRADATION,
                severity=severity,
                affected_entity=bank,
                affected_transactions=stats.count,
                baseline_value=baseline,
                current_value=current_rate,
                z_score=z_score,
                confidence=confidence,
                metadata={"detection_method": "z_score_baseline"}
            )
        
        # Update baseline slowly
        self.baselines[baseline_key] = baseline * 0.99 + current_rate * 0.01
        
        return None
    
    def _detect_retry_storm(self) -> Optional[Pattern]:
        """Detect retry storm patterns."""
        if self.retry_tracker.count < self.config.min_sample_size:
            return None
        
        retry_ratio = self.retry_tracker.mean
        
        if retry_ratio >= self.config.retry_ratio_threshold:
            severity = min(1.0, retry_ratio / 0.5)  # 50% retries = max severity
            confidence = min(0.95, 0.6 + self.retry_tracker.count / 50)
            
            return Pattern(
                pattern_type=PatternType.RETRY_STORM,
                severity=severity,
                affected_entity="system",
                affected_transactions=self.retry_tracker.count,
                baseline_value=self.config.retry_ratio_threshold,
                current_value=retry_ratio,
                z_score=0,  # Not applicable
                confidence=confidence,
                metadata={"retry_count": int(retry_ratio * self.retry_tracker.count)}
            )
        
        return None
    
    def _detect_method_fatigue(self, method: str) -> Optional[Pattern]:
        """Detect payment method fatigue."""
        stats = self.method_success_rates[method]
        
        if stats.count < self.config.min_sample_size:
            return None
        
        baseline_key = f"method_{method}_success"
        baseline = self.baselines.get(baseline_key, 0.93)
        
        current_rate = stats.mean
        drop = baseline - current_rate
        
        if drop >= self.config.method_fatigue_drop:
            severity = min(1.0, drop / 0.2)  # 20% drop = max severity
            confidence = min(0.95, 0.5 + stats.count / 100)
            
            return Pattern(
                pattern_type=PatternType.METHOD_FATIGUE,
                severity=severity,
                affected_entity=method,
                affected_transactions=stats.count,
                baseline_value=baseline,
                current_value=current_rate,
                z_score=drop / 0.05 if 0.05 > 0 else 0,  # Standardized drop
                confidence=confidence,
                metadata={"success_drop": drop}
            )
        
        # Update baseline
        self.baselines[baseline_key] = baseline * 0.99 + current_rate * 0.01
        
        return None
    
    def _detect_latency_spike(self, gateway: str) -> Optional[Pattern]:
        """Detect latency spikes on gateways."""
        stats = self.gateway_latencies[gateway]
        
        if stats.count < self.config.min_sample_size // 2:  # Lower threshold for latency
            return None
        
        baseline_key = f"gateway_{gateway}_p95"
        baseline_p95 = self.baselines.get(baseline_key, 2000)
        
        current_p95 = stats.get_percentile(95)
        
        # Check for spike
        if current_p95 > baseline_p95 * 1.5:  # 50% increase
            z_score = stats.get_z_score(current_p95)
            
            if z_score >= self.config.latency_spike_zscore:
                severity = min(1.0, (current_p95 / baseline_p95 - 1) / 2)
                confidence = min(0.95, 0.5 + stats.count / 50)
                
                return Pattern(
                    pattern_type=PatternType.LATENCY_SPIKE,
                    severity=severity,
                    affected_entity=gateway,
                    affected_transactions=stats.count,
                    baseline_value=baseline_p95,
                    current_value=current_p95,
                    z_score=z_score,
                    confidence=confidence,
                    metadata={"p50": stats.get_percentile(50), "p99": stats.get_percentile(99)}
                )
        
        # Update baseline slowly
        self.baselines[baseline_key] = baseline_p95 * 0.98 + current_p95 * 0.02
        
        return None
    
    def _detect_error_clustering(self) -> Optional[Pattern]:
        """Detect clustering of specific error codes."""
        total_errors = sum(self.error_counts.values())
        
        if total_errors < self.config.min_sample_size:
            return None
        
        # Find dominant error
        max_error = max(self.error_counts.items(), key=lambda x: x[1])
        error_code, count = max_error
        ratio = count / total_errors
        
        if ratio >= self.config.error_cluster_threshold:
            severity = min(1.0, ratio / 0.5)
            confidence = min(0.95, 0.5 + total_errors / 100)
            
            return Pattern(
                pattern_type=PatternType.ERROR_CLUSTERING,
                severity=severity,
                affected_entity=error_code,
                affected_transactions=count,
                baseline_value=self.config.error_cluster_threshold,
                current_value=ratio,
                z_score=0,
                confidence=confidence,
                metadata={"error_distribution": dict(self.error_counts)}
            )
        
        return None
    
    def _update_error_counts(self, error_code: str):
        """Update error counts with windowing."""
        now = datetime.now()
        
        # Reset window if expired
        if (now - self.error_window_start).total_seconds() > self.config.medium_window:
            self.error_counts = defaultdict(int)
            self.error_window_start = now
        
        self.error_counts[error_code] += 1
    
    def _generate_hypothesis(self, pattern: Pattern) -> Optional[Hypothesis]:
        """Generate a hypothesis for a detected pattern."""
        hypothesis_generators = {
            PatternType.ISSUER_DEGRADATION: self._hypothesis_for_issuer_degradation,
            PatternType.RETRY_STORM: self._hypothesis_for_retry_storm,
            PatternType.METHOD_FATIGUE: self._hypothesis_for_method_fatigue,
            PatternType.LATENCY_SPIKE: self._hypothesis_for_latency_spike,
            PatternType.ERROR_CLUSTERING: self._hypothesis_for_error_clustering,
        }
        
        generator = hypothesis_generators.get(pattern.pattern_type)
        if generator:
            return generator(pattern)
        return None
    
    def _hypothesis_for_issuer_degradation(self, pattern: Pattern) -> Hypothesis:
        """Generate hypothesis for issuer degradation."""
        bank = pattern.affected_entity
        drop = pattern.baseline_value - pattern.current_value
        
        # Determine likely root cause based on error distribution
        root_causes = [
            f"Bank infrastructure issues at {bank}",
            f"Throttling by {bank} due to high volume",
            f"Maintenance window at {bank}",
            f"Network connectivity issues with {bank}"
        ]
        
        return Hypothesis(
            pattern_id=pattern.id,
            pattern_type=pattern.pattern_type,
            description=f"Issuer {bank} is experiencing degraded performance with {drop:.1%} success rate drop",
            root_cause=root_causes[0],  # Primary hypothesis
            confidence=pattern.confidence,
            supporting_evidence=[
                f"Success rate dropped from {pattern.baseline_value:.1%} to {pattern.current_value:.1%}",
                f"Z-score of {pattern.z_score:.2f} indicates significant deviation",
                f"Affected {pattern.affected_transactions} transactions"
            ]
        )
    
    def _hypothesis_for_retry_storm(self, pattern: Pattern) -> Hypothesis:
        """Generate hypothesis for retry storm."""
        return Hypothesis(
            pattern_id=pattern.id,
            pattern_type=pattern.pattern_type,
            description=f"Retry storm detected with {pattern.current_value:.1%} retry ratio",
            root_cause="Cascading failures triggering excessive retries",
            confidence=pattern.confidence,
            supporting_evidence=[
                f"Retry ratio of {pattern.current_value:.1%} exceeds threshold of {pattern.baseline_value:.1%}",
                f"System under increased load from retry traffic"
            ]
        )
    
    def _hypothesis_for_method_fatigue(self, pattern: Pattern) -> Hypothesis:
        """Generate hypothesis for method fatigue."""
        method = pattern.affected_entity
        return Hypothesis(
            pattern_id=pattern.id,
            pattern_type=pattern.pattern_type,
            description=f"Payment method {method.upper()} showing performance degradation",
            root_cause=f"Infrastructure or integration issues with {method} payment rails",
            confidence=pattern.confidence,
            supporting_evidence=[
                f"Success rate dropped from {pattern.baseline_value:.1%} to {pattern.current_value:.1%}",
                f"Pattern persisting over observation window"
            ]
        )
    
    def _hypothesis_for_latency_spike(self, pattern: Pattern) -> Hypothesis:
        """Generate hypothesis for latency spike."""
        gateway = pattern.affected_entity
        return Hypothesis(
            pattern_id=pattern.id,
            pattern_type=pattern.pattern_type,
            description=f"Latency spike on gateway {gateway}",
            root_cause=f"Gateway {gateway} experiencing high load or infrastructure issues",
            confidence=pattern.confidence,
            supporting_evidence=[
                f"P95 latency increased from {pattern.baseline_value:.0f}ms to {pattern.current_value:.0f}ms",
                f"Z-score of {pattern.z_score:.2f} indicates anomaly"
            ]
        )
    
    def _hypothesis_for_error_clustering(self, pattern: Pattern) -> Hypothesis:
        """Generate hypothesis for error clustering."""
        error_code = pattern.affected_entity
        return Hypothesis(
            pattern_id=pattern.id,
            pattern_type=pattern.pattern_type,
            description=f"Error code {error_code} dominating failure distribution",
            root_cause=f"Specific failure mode indicated by {error_code}",
            confidence=pattern.confidence,
            supporting_evidence=[
                f"{error_code} represents {pattern.current_value:.1%} of all errors",
                f"Concentrated failure pattern suggests single root cause"
            ]
        )
    
    def _is_duplicate_pattern(self, pattern: Pattern) -> bool:
        """Check if a similar pattern already exists."""
        for existing in self.active_patterns:
            if (existing.pattern_type == pattern.pattern_type and
                existing.affected_entity == pattern.affected_entity and
                (datetime.now() - existing.detected_at).total_seconds() < 60):
                return True
        return False
    
    def _cleanup_old_patterns(self):
        """Remove patterns older than the long window."""
        cutoff = datetime.now() - timedelta(seconds=self.config.long_window)
        self.active_patterns = [p for p in self.active_patterns if p.detected_at > cutoff]
        
        # Also clean up hypotheses
        self.active_hypotheses = [h for h in self.active_hypotheses if not h.is_expired]
    
    def get_active_patterns(self) -> List[Dict]:
        """Get currently active patterns."""
        return [p.to_dict() for p in self.active_patterns]
    
    def get_active_hypotheses(self) -> List[Dict]:
        """Get currently active hypotheses."""
        return [h.to_dict() for h in self.active_hypotheses if h.is_actionable]
    
    def get_stats(self) -> Dict:
        """Get detector statistics."""
        return {
            "active_patterns": len(self.active_patterns),
            "active_hypotheses": len([h for h in self.active_hypotheses if h.is_actionable]),
            "total_patterns_detected": len(self.pattern_history),
            "banks_monitored": len(self.bank_success_rates),
            "methods_monitored": len(self.method_success_rates),
            "gateways_monitored": len(self.gateway_latencies),
            "baselines_learned": len(self.baselines)
        }
