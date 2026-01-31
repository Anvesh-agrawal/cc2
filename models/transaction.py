"""
Transaction Models
==================
Data classes for payment transactions and related entities.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict
import uuid

from config import PaymentMethod, TransactionStatus


@dataclass
class Transaction:
    """Represents a single payment transaction."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Payment details
    amount: float = 0.0
    currency: str = "INR"
    payment_method: PaymentMethod = PaymentMethod.CARD
    
    # Bank/Issuer info
    issuer_bank: str = ""
    acquiring_bank: str = ""
    
    # Route info
    gateway: str = ""
    route_id: str = ""
    
    # Outcome
    status: TransactionStatus = TransactionStatus.PENDING
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    
    # Performance
    latency_ms: float = 0.0
    processing_cost: float = 0.0
    
    # Retry info
    is_retry: bool = False
    retry_count: int = 0
    original_txn_id: Optional[str] = None
    
    # Metadata
    merchant_id: str = ""
    customer_id: str = ""
    region: str = "IN"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for DataFrame compatibility."""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "amount": self.amount,
            "currency": self.currency,
            "payment_method": self.payment_method.value,
            "issuer_bank": self.issuer_bank,
            "acquiring_bank": self.acquiring_bank,
            "gateway": self.gateway,
            "route_id": self.route_id,
            "status": self.status.value,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "latency_ms": self.latency_ms,
            "processing_cost": self.processing_cost,
            "is_retry": self.is_retry,
            "retry_count": self.retry_count,
            "original_txn_id": self.original_txn_id,
            "merchant_id": self.merchant_id,
            "customer_id": self.customer_id,
            "region": self.region
        }
    
    @property
    def is_successful(self) -> bool:
        return self.status == TransactionStatus.SUCCESS
    
    @property
    def is_failed(self) -> bool:
        return self.status in [TransactionStatus.FAILURE, TransactionStatus.TIMEOUT]


@dataclass
class TransactionBatch:
    """A batch of transactions for analysis."""
    transactions: List[Transaction] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    @property
    def count(self) -> int:
        return len(self.transactions)
    
    @property
    def success_count(self) -> int:
        return sum(1 for t in self.transactions if t.is_successful)
    
    @property
    def failure_count(self) -> int:
        return sum(1 for t in self.transactions if t.is_failed)
    
    @property
    def success_rate(self) -> float:
        if self.count == 0:
            return 0.0
        return self.success_count / self.count
    
    @property
    def avg_latency(self) -> float:
        if self.count == 0:
            return 0.0
        return sum(t.latency_ms for t in self.transactions) / self.count
    
    @property
    def retry_rate(self) -> float:
        if self.count == 0:
            return 0.0
        return sum(1 for t in self.transactions if t.is_retry) / self.count
    
    def filter_by_bank(self, bank: str) -> 'TransactionBatch':
        """Filter transactions by issuer bank."""
        filtered = [t for t in self.transactions if t.issuer_bank == bank]
        return TransactionBatch(transactions=filtered, start_time=self.start_time)
    
    def filter_by_method(self, method: PaymentMethod) -> 'TransactionBatch':
        """Filter transactions by payment method."""
        filtered = [t for t in self.transactions if t.payment_method == method]
        return TransactionBatch(transactions=filtered, start_time=self.start_time)
    
    def filter_by_status(self, status: TransactionStatus) -> 'TransactionBatch':
        """Filter transactions by status."""
        filtered = [t for t in self.transactions if t.status == status]
        return TransactionBatch(transactions=filtered, start_time=self.start_time)
    
    def get_error_distribution(self) -> Dict[str, int]:
        """Get distribution of error codes."""
        distribution = {}
        for t in self.transactions:
            if t.error_code:
                distribution[t.error_code] = distribution.get(t.error_code, 0) + 1
        return distribution
    
    def get_bank_stats(self) -> Dict[str, Dict]:
        """Get success rates by bank."""
        stats = {}
        for t in self.transactions:
            bank = t.issuer_bank
            if bank not in stats:
                stats[bank] = {"total": 0, "success": 0}
            stats[bank]["total"] += 1
            if t.is_successful:
                stats[bank]["success"] += 1
        
        for bank in stats:
            total = stats[bank]["total"]
            success = stats[bank]["success"]
            stats[bank]["success_rate"] = success / total if total > 0 else 0.0
        
        return stats
    
    def get_method_stats(self) -> Dict[str, Dict]:
        """Get success rates by payment method."""
        stats = {}
        for t in self.transactions:
            method = t.payment_method.value
            if method not in stats:
                stats[method] = {"total": 0, "success": 0, "total_latency": 0}
            stats[method]["total"] += 1
            stats[method]["total_latency"] += t.latency_ms
            if t.is_successful:
                stats[method]["success"] += 1
        
        for method in stats:
            total = stats[method]["total"]
            success = stats[method]["success"]
            stats[method]["success_rate"] = success / total if total > 0 else 0.0
            stats[method]["avg_latency"] = stats[method]["total_latency"] / total if total > 0 else 0.0
        
        return stats


@dataclass
class RouteStats:
    """Statistics for a payment route (bank + method + gateway combination)."""
    route_id: str
    bank: str
    payment_method: PaymentMethod
    gateway: str
    
    # Bayesian parameters for Thompson Sampling
    alpha: float = 1.0  # Success count + 1 (prior)
    beta: float = 1.0   # Failure count + 1 (prior)
    
    # Performance metrics
    total_transactions: int = 0
    successful_transactions: int = 0
    failed_transactions: int = 0
    total_latency: float = 0.0
    total_cost: float = 0.0
    
    # Recent performance (for quick checks)
    recent_success_rate: float = 0.0
    recent_avg_latency: float = 0.0
    
    # Suppression state
    is_suppressed: bool = False
    suppression_reason: Optional[str] = None
    suppression_until: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        if self.total_transactions == 0:
            return 0.0
        return self.successful_transactions / self.total_transactions
    
    @property
    def avg_latency(self) -> float:
        if self.total_transactions == 0:
            return 0.0
        return self.total_latency / self.total_transactions
    
    @property
    def avg_cost(self) -> float:
        if self.total_transactions == 0:
            return 0.0
        return self.total_cost / self.total_transactions
    
    def update(self, transaction: Transaction):
        """Update stats with a new transaction."""
        self.total_transactions += 1
        self.total_latency += transaction.latency_ms
        self.total_cost += transaction.processing_cost
        
        if transaction.is_successful:
            self.successful_transactions += 1
            self.alpha += 1
        else:
            self.failed_transactions += 1
            self.beta += 1
    
    def get_thompson_sample(self) -> float:
        """Sample from Beta distribution for Thompson Sampling."""
        import numpy as np
        return np.random.beta(self.alpha, self.beta)
    
    def to_dict(self) -> Dict:
        return {
            "route_id": self.route_id,
            "bank": self.bank,
            "payment_method": self.payment_method.value,
            "gateway": self.gateway,
            "success_rate": self.success_rate,
            "avg_latency": self.avg_latency,
            "total_transactions": self.total_transactions,
            "is_suppressed": self.is_suppressed
        }
