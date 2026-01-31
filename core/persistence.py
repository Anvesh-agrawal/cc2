"""
State Persistence
=================
SQLite-based persistence for router state and learning across restarts.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, Optional, Any
from dataclasses import asdict


class StatePersistence:
    """Persist agent state to SQLite for learning continuity."""
    
    def __init__(self, db_path: str = "antigravity_state.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Route statistics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS route_stats (
                route_id TEXT PRIMARY KEY,
                bank TEXT,
                payment_method TEXT,
                gateway TEXT,
                alpha REAL DEFAULT 1.0,
                beta REAL DEFAULT 1.0,
                total_transactions INTEGER DEFAULT 0,
                successful_transactions INTEGER DEFAULT 0,
                total_latency REAL DEFAULT 0.0,
                total_cost REAL DEFAULT 0.0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Margin tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS margin_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                smart_margin REAL DEFAULT 0.0,
                baseline_margin REAL DEFAULT 0.0,
                margin_generated REAL DEFAULT 0.0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Shadow mode predictions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shadow_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction TEXT,
                actual_outcome TEXT,
                was_correct INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def save_route_stats(self, route_id: str, stats: Dict):
        """Save route statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO route_stats 
            (route_id, bank, payment_method, gateway, alpha, beta, 
             total_transactions, successful_transactions, total_latency, total_cost, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            route_id,
            stats.get("bank", ""),
            stats.get("payment_method", ""),
            stats.get("gateway", ""),
            stats.get("alpha", 1.0),
            stats.get("beta", 1.0),
            stats.get("total_transactions", 0),
            stats.get("successful_transactions", 0),
            stats.get("total_latency", 0.0),
            stats.get("total_cost", 0.0),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def load_route_stats(self, route_id: str) -> Optional[Dict]:
        """Load route statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM route_stats WHERE route_id = ?
        """, (route_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "route_id": row[0],
                "bank": row[1],
                "payment_method": row[2],
                "gateway": row[3],
                "alpha": row[4],
                "beta": row[5],
                "total_transactions": row[6],
                "successful_transactions": row[7],
                "total_latency": row[8],
                "total_cost": row[9],
                "last_updated": row[10]
            }
        return None
    
    def load_all_route_stats(self) -> Dict[str, Dict]:
        """Load all route statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM route_stats")
        rows = cursor.fetchall()
        conn.close()
        
        result = {}
        for row in rows:
            result[row[0]] = {
                "route_id": row[0],
                "bank": row[1],
                "payment_method": row[2],
                "gateway": row[3],
                "alpha": row[4],
                "beta": row[5],
                "total_transactions": row[6],
                "successful_transactions": row[7],
                "total_latency": row[8],
                "total_cost": row[9],
                "last_updated": row[10]
            }
        return result
    
    def save_margin_stats(self, smart_margin: float, baseline_margin: float):
        """Save margin statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO margin_stats (smart_margin, baseline_margin, margin_generated)
            VALUES (?, ?, ?)
        """, (smart_margin, baseline_margin, smart_margin - baseline_margin))
        
        conn.commit()
        conn.close()
    
    def load_latest_margin_stats(self) -> Dict:
        """Load latest margin statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT smart_margin, baseline_margin, margin_generated 
            FROM margin_stats 
            ORDER BY timestamp DESC LIMIT 1
        """)
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "smart_margin": row[0],
                "baseline_margin": row[1],
                "margin_generated": row[2]
            }
        return {"smart_margin": 0.0, "baseline_margin": 0.0, "margin_generated": 0.0}
    
    def save_all_router_state(self, router):
        """Save entire router state."""
        # Save all route stats
        for route_id, route in router.routes.items():
            self.save_route_stats(route_id, {
                "bank": route.bank,
                "payment_method": route.payment_method.value if hasattr(route.payment_method, 'value') else str(route.payment_method),
                "gateway": route.gateway,
                "alpha": route.alpha,
                "beta": route.beta,
                "total_transactions": route.total_transactions,
                "successful_transactions": route.successful_transactions,
                "total_latency": route.total_latency,
                "total_cost": route.total_cost
            })
        
        # Save margin stats
        self.save_margin_stats(router.smart_margin, router.baseline_margin)
    
    def restore_router_state(self, router):
        """Restore router state from database."""
        from config import PaymentMethod
        from models.transaction import RouteStats
        
        # Load route stats
        all_stats = self.load_all_route_stats()
        
        for route_id, stats in all_stats.items():
            # Convert payment method string to enum
            method_str = stats.get("payment_method", "card")
            try:
                payment_method = PaymentMethod(method_str)
            except ValueError:
                payment_method = PaymentMethod.CARD
            
            # Create or update route
            if route_id not in router.routes:
                router.routes[route_id] = RouteStats(
                    route_id=route_id,
                    bank=stats.get("bank", ""),
                    payment_method=payment_method,
                    gateway=stats.get("gateway", "")
                )
            
            # Restore learned parameters
            route = router.routes[route_id]
            route.alpha = stats.get("alpha", 1.0)
            route.beta = stats.get("beta", 1.0)
            route.total_transactions = stats.get("total_transactions", 0)
            route.successful_transactions = stats.get("successful_transactions", 0)
            route.total_latency = stats.get("total_latency", 0.0)
            route.total_cost = stats.get("total_cost", 0.0)
            
            router.traffic_weights[route_id] = 1.0
        
        # Load margin stats
        margin_stats = self.load_latest_margin_stats()
        router.smart_margin = margin_stats.get("smart_margin", 0.0)
        router.baseline_margin = margin_stats.get("baseline_margin", 0.0)
        router.margin_generated = margin_stats.get("margin_generated", 0.0)
