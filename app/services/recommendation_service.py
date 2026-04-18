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
        exclude_set = set(exclude_product_ids or [])

        feature_row = self.repo.get_customer_features(tenant_id, customer_id)
        anchor_products = self.repo.get_recent_anchor_products(tenant_id, customer_id, limit=5)

        candidates: dict[str, dict] = {}

        if feature_row and feature_row.get("category_affinity"):
            affinity_candidates = self.repo.get_products_by_category_affinity(
                tenant_id=tenant_id,
                category_affinity=feature_row["category_affinity"],
                limit=100,
            )

            for row in affinity_candidates:
                product_id = str(row["product_id"])
                if product_id in exclude_set:
                    continue
                candidates.setdefault(product_id, {
                    "category_score": 0.0,
                    "cooccurrence_score": 0.0,
                    "reason": "category_affinity",
                })
                candidates[product_id]["category_score"] = max(
                    candidates[product_id]["category_score"],
                    float(row["score"]),
                )

        for anchor_product in anchor_products:
            related_rows = self.repo.get_top_related_products(
                tenant_id=tenant_id,
                product_id=anchor_product,
                limit=50,
            )
            for row in related_rows:
                product_id = str(row["product_id"])
                if product_id in exclude_set or product_id == anchor_product:
                    continue

                candidates.setdefault(product_id, {
                    "category_score": 0.0,
                    "cooccurrence_score": 0.0,
                    "reason": "cooccurrence",
                })

                candidates[product_id]["cooccurrence_score"] = max(
                    candidates[product_id]["cooccurrence_score"],
                    float(row["confidence"]),
                )

                if candidates[product_id]["category_score"] > 0:
                    candidates[product_id]["reason"] = "blended"

        if not candidates:
            popularity_rows = self.repo.get_global_popularity(tenant_id=tenant_id, limit=limit * 3)
            for row in popularity_rows:
                product_id = str(row["product_id"])
                if product_id in exclude_set:
                    continue
                candidates[product_id] = {
                    "category_score": 0.0,
                    "cooccurrence_score": float(row["score"]),
                    "reason": "global_popularity",
                }

        ranked_items = []
        for product_id, values in candidates.items():
            if values["reason"] == "global_popularity":
                final_score = values["cooccurrence_score"]
            else:
                final_score = (
                    0.6 * values["category_score"] +
                    0.4 * values["cooccurrence_score"]
                )

            ranked_items.append({
                "product_id": product_id,
                "score": round(final_score, 4),
                "reason": values["reason"],
            })

        ranked_items.sort(key=lambda x: (-x["score"], x["product_id"]))
        ranked_items = ranked_items[:limit]

        decision_id = str(uuid4())
        latency_ms = round((time.perf_counter() - started) * 1000, 2)

        self.repo.log_recommendation_decision(
            tenant_id=tenant_id,
            customer_id=customer_id,
            surface=surface,
            decision_id=decision_id,
            model_version=self.MODEL_VERSION,
            response_items=ranked_items,
            latency_ms=latency_ms,
        )

        return {
            "items": ranked_items,
            "model_version": self.MODEL_VERSION,
            "decision_id": decision_id,
            "latency_ms": latency_ms,
        }