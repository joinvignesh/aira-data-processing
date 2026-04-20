# app/services/recommendation_service.py

from __future__ import annotations
import time
from uuid import uuid4

class RecommendationService:
    MODEL_VERSION = "v1-blended-heuristic"

    def __init__(self, repo):
        self.repo = repo

    def recommend(
        self,
        tenant_id: str,
        customer_id: str,
        surface: str,
        limit: int,
        exclude_product_ids: list[str] | None = None,
    ) -> dict:
        started = time.perf_counter()
        # Using a set for O(1) lookup speed
        exclude_set = set(exclude_product_ids) if exclude_product_ids else set()
        
        # 1. Fetch context (Features and Anchors)
        feature_row = self.repo.get_customer_features(tenant_id, customer_id)
        anchor_products = self.repo.get_recent_anchor_products(tenant_id, customer_id, limit=5)

        candidates: dict[str, dict] = {}

        # 2. Category Affinity Logic
        if feature_row and (affinity := feature_row.get("category_affinity")):
            affinity_candidates = self.repo.get_products_by_category_affinity(
                tenant_id=tenant_id,
                category_affinity=affinity,
                limit=100,
            )

            for row in affinity_candidates:
                p_id = str(row["product_id"])
                if p_id in exclude_set:
                    continue
                candidates[p_id] = {
                    "category_score": float(row["score"]),
                    "cooccurrence_score": 0.0,
                    "reason": "category_affinity",
                }

        # 3. Optimized Batch Related Products
        if anchor_products:
            related_rows = self.repo.get_top_related_products_batch(
                tenant_id=tenant_id,
                product_ids=anchor_products,
                limit_per_product=50,
            )
            
            for row in related_rows:
                p_id = str(row["product_id"])
                anchor_id = str(row.get("anchor_product_id"))
                
                if p_id in exclude_set or p_id == anchor_id:
                    continue

                # Get existing candidate or create new one (minimizes dict lookups)
                can = candidates.get(p_id)
                if not can:
                    candidates[p_id] = {
                        "category_score": 0.0,
                        "cooccurrence_score": float(row["confidence"]),
                        "reason": "cooccurrence",
                    }
                else:
                    # Update existing candidate
                    can["cooccurrence_score"] = max(can["cooccurrence_score"], float(row["confidence"]))
                    if can["category_score"] > 0:
                        can["reason"] = "blended"

        # 4. Fallback Logic (Only if no candidates found yet)
        if not candidates:
            popularity_rows = self.repo.get_global_popularity(tenant_id=tenant_id, limit=limit * 3)
            candidates = {
                (p_id := str(row["product_id"])): {
                    "category_score": 0.0,
                    "cooccurrence_score": float(row["score"]),
                    "reason": "global_popularity",
                }
                for row in popularity_rows if str(row["product_id"]) not in exclude_set
            }

        # 5. OPTIMIZED RANKING: List Comprehension
        # We calculate the score and build the dict in one pass at C-speed.
        ranked_items = [
            {
                "product_id": p_id,
                "score": round(
                    (v["cooccurrence_score"] if v["reason"] == "global_popularity" 
                     else (0.6 * v["category_score"] + 0.4 * v["cooccurrence_score"])), 
                    4
                ),
                "reason": v["reason"],
            }
            for p_id, v in candidates.items()
        ]

        # Sorting is Timsort (O(n log n)), very efficient in Python
        ranked_items.sort(key=lambda x: (-x["score"], x["product_id"]))
        
        # Slicing the list is efficient
        final_items = ranked_items[:limit]

        decision_id = str(uuid4())
        latency_ms = round((time.perf_counter() - started) * 1000, 2)

        # 6. Prepare payload for Background Task
        log_payload = {
            "tenant_id": tenant_id,
            "customer_id": customer_id,
            "surface": surface,
            "decision_id": decision_id,
            "model_version": self.MODEL_VERSION,
            "response_items": final_items,
            "latency_ms": latency_ms,
        }

        return {
            "items": final_items,
            "model_version": self.MODEL_VERSION,
            "decision_id": decision_id,
            "latency_ms": latency_ms,
            "_log_payload": log_payload
        }