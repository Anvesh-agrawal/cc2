"""
Bayesian Router
===============
Thompson Sampling-based probabilistic router for payment optimization.
"""

import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass, field

from config import PaymentMethod, OptimizerConfig, config
from models.transaction import Transaction, RouteStats


class BayesianRouter:
    """
    Probabilistic payment router using Thompson Sampling.
    
    Features:
    - Multi-armed bandit approach for route selection
    - Balances exploration and exploitation
    - Multi-factor optimization (success, latency, cost)
    - Maintains Beta distribution priors per route
    """
    
    def __init__(self, config: OptimizerConfig = None):
        self.config = config or OptimizerConfig()
        
        # Route statistics with Bayesian priors
        self.routes: Dict[str, RouteStats] = {}
        
        # Traffic allocation weights (dynamically adjusted)
        self.traffic_weights: Dict[str, float] = {}
        
        # Historical performance
        self.route_history: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        
        # Suppressed routes
        self.suppressed_routes: Dict[str, datetime] = {}
    
    def register_route(
        self,
        bank: str,
        payment_method: PaymentMethod,
        gateway: str
    ) -> str:
        """Register a new route for tracking."""
        route_id = f"{bank}_{payment_method.value}_{gateway}"
        
        if route_id not in self.routes:
            self.routes[route_id] = RouteStats(
                route_id=route_id,
                bank=bank,
                payment_method=payment_method,
                gateway=gateway
            )
            self.traffic_weights[route_id] = 1.0
        
        return route_id
    
    def update_route(self, transaction: Transaction):
        """Update route statistics with a new transaction."""
        route_id = transaction.route_id
        
        # Register if new
        if route_id not in self.routes:
            self.routes[route_id] = RouteStats(
                route_id=route_id,
                bank=transaction.issuer_bank,
                payment_method=transaction.payment_method,
                gateway=transaction.gateway
            )
            self.traffic_weights[route_id] = 1.0
        
        # Update stats
        self.routes[route_id].update(transaction)
        
        # Record in history
        self.route_history[route_id].append(
            (datetime.now(), 1.0 if transaction.is_successful else 0.0)
        )
        
        # Cleanup old history (keep last hour)
        cutoff = datetime.now() - timedelta(hours=1)
        self.route_history[route_id] = [
            (ts, v) for ts, v in self.route_history[route_id] if ts > cutoff
        ]
    
    def select_route(
        self,
        bank: str,
        payment_method: PaymentMethod,
        available_gateways: List[str] = None
    ) -> Tuple[str, Dict]:
        """
        Select the best route using Thompson Sampling.
        
        Returns:
            Tuple of (route_id, selection_metadata)
        """
        if available_gateways is None:
            available_gateways = ["razorpay", "paytm", "phonepe", "billdesk", "ccavenue"]
        
        candidates = []
        now = datetime.now()
        
        for gateway in available_gateways:
            route_id = f"{bank}_{payment_method.value}_{gateway}"
            
            # Skip suppressed routes
            if route_id in self.suppressed_routes:
                if now < self.suppressed_routes[route_id]:
                    continue
                else:
                    del self.suppressed_routes[route_id]
            
            # Get or create route stats
            if route_id not in self.routes:
                self.register_route(bank, payment_method, gateway)
            
            route = self.routes[route_id]
            
            # Thompson Sampling: sample from Beta distribution
            success_sample = route.get_thompson_sample()
            
            # Add exploration bonus for less-tried routes
            exploration_bonus = self.config.exploration_bonus / (1 + np.log1p(route.total_transactions))
            
            # Calculate composite score
            score = self._calculate_route_score(route, success_sample, exploration_bonus)
            
            candidates.append({
                "route_id": route_id,
                "gateway": gateway,
                "score": score,
                "success_sample": success_sample,
                "historical_success": route.success_rate,
                "avg_latency": route.avg_latency,
                "total_transactions": route.total_transactions,
                "exploration_bonus": exploration_bonus
            })
        
        if not candidates:
            # No available routes, return a default
            default_route = f"{bank}_{payment_method.value}_{available_gateways[0]}"
            return default_route, {"error": "all_routes_suppressed", "fallback": True}
        
        # Select best route
        best = max(candidates, key=lambda x: x["score"])
        
        # Apply traffic weight adjustment
        if best["route_id"] in self.traffic_weights:
            weight = self.traffic_weights[best["route_id"]]
            if np.random.random() > weight:
                # Probabilistically pick second best
                sorted_candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)
                if len(sorted_candidates) > 1:
                    best = sorted_candidates[1]
        
        return best["route_id"], {
            "selected_gateway": best["gateway"],
            "selection_score": best["score"],
            "success_probability": best["success_sample"],
            "historical_success": best["historical_success"],
            "avg_latency": best["avg_latency"],
            "candidates_evaluated": len(candidates),
            "exploration_bonus": best["exploration_bonus"]
        }
    
    def _calculate_route_score(
        self,
        route: RouteStats,
        success_sample: float,
        exploration_bonus: float
    ) -> float:
        """Calculate composite score for a route."""
        # Normalize latency (lower is better, cap at 5000ms)
        latency_score = 1.0 - min(route.avg_latency, 5000) / 5000
        
        # Normalize cost (lower is better, cap at 5.0)
        cost_score = 1.0 - min(route.avg_cost, 5.0) / 5.0
        
        # Weighted composite
        score = (
            self.config.success_weight * success_sample +
            self.config.latency_weight * latency_score +
            self.config.cost_weight * cost_score +
            exploration_bonus
        )
        
        return score
    
    def adjust_traffic_weight(self, route_id: str, weight: float):
        """Adjust traffic allocation weight for a route."""
        self.traffic_weights[route_id] = max(0.0, min(1.0, weight))
    
    def suppress_route(self, route_id: str, duration_seconds: int, reason: str = ""):
        """Temporarily suppress a route."""
        if route_id in self.routes:
            self.routes[route_id].is_suppressed = True
            self.routes[route_id].suppression_reason = reason
            self.suppressed_routes[route_id] = datetime.now() + timedelta(seconds=duration_seconds)
    
    def unsuppress_route(self, route_id: str):
        """Remove suppression from a route."""
        if route_id in self.routes:
            self.routes[route_id].is_suppressed = False
            self.routes[route_id].suppression_reason = None
        if route_id in self.suppressed_routes:
            del self.suppressed_routes[route_id]
    
    def get_route_recommendations(
        self,
        bank: str,
        payment_method: PaymentMethod,
        top_n: int = 3
    ) -> List[Dict]:
        """Get top N route recommendations with explanations."""
        candidates = []
        
        for route_id, route in self.routes.items():
            if route.bank == bank and route.payment_method == payment_method:
                if route_id not in self.suppressed_routes:
                    success_sample = route.get_thompson_sample()
                    score = self._calculate_route_score(route, success_sample, 0)
                    candidates.append({
                        "route_id": route_id,
                        "gateway": route.gateway,
                        "score": round(score, 4),
                        "success_rate": round(route.success_rate, 4),
                        "avg_latency": round(route.avg_latency, 2),
                        "avg_cost": round(route.avg_cost, 2),
                        "transaction_count": route.total_transactions,
                        "confidence": min(0.95, route.total_transactions / 100)
                    })
        
        # Sort by score and return top N
        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:top_n]
    
    def get_all_routes(self) -> List[Dict]:
        """Get statistics for all routes."""
        return [route.to_dict() for route in self.routes.values()]
    
    def get_suppressed_routes(self) -> List[Dict]:
        """Get list of suppressed routes."""
        now = datetime.now()
        suppressed = []
        for route_id, until in self.suppressed_routes.items():
            if route_id in self.routes:
                route = self.routes[route_id]
                suppressed.append({
                    "route_id": route_id,
                    "reason": route.suppression_reason,
                    "until": until,
                    "remaining_seconds": max(0, (until - now).total_seconds())
                })
        return suppressed
    
    def get_route_performance(self, route_id: str, window_seconds: int = 300) -> Dict:
        """Get recent performance metrics for a route."""
        if route_id not in self.routes:
            return {"error": "route_not_found"}
        
        route = self.routes[route_id]
        history = self.route_history.get(route_id, [])
        
        # Filter to window
        cutoff = datetime.now() - timedelta(seconds=window_seconds)
        recent = [v for ts, v in history if ts > cutoff]
        
        recent_success_rate = sum(recent) / len(recent) if recent else 0.0
        
        return {
            "route_id": route_id,
            "overall_success_rate": route.success_rate,
            "recent_success_rate": recent_success_rate,
            "avg_latency": route.avg_latency,
            "total_transactions": route.total_transactions,
            "recent_transactions": len(recent),
            "alpha": route.alpha,
            "beta": route.beta,
            "is_suppressed": route.is_suppressed
        }
    
    def reset_route_priors(self, route_id: str):
        """Reset Bayesian priors for a route."""
        if route_id in self.routes:
            self.routes[route_id].alpha = 1.0
            self.routes[route_id].beta = 1.0
    
    def get_stats(self) -> Dict:
        """Get router statistics."""
        active_routes = [r for r in self.routes.values() if not r.is_suppressed]
        suppressed_routes = [r for r in self.routes.values() if r.is_suppressed]
        
        return {
            "total_routes": len(self.routes),
            "active_routes": len(active_routes),
            "suppressed_routes": len(suppressed_routes),
            "best_performing": sorted(
                [r.route_id for r in active_routes],
                key=lambda x: self.routes[x].success_rate,
                reverse=True
            )[:3] if active_routes else [],
            "worst_performing": sorted(
                [r.route_id for r in active_routes],
                key=lambda x: self.routes[x].success_rate
            )[:3] if active_routes else []
        }
