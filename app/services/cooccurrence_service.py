# app/services/cooccurrence_service.py

from __future__ import annotations


class CooccurrenceService:
    def __init__(self, repo):
        self.repo = repo

    def get_related_products(
        self,
        tenant_id: str,
        product_id: str,
        limit: int = 10,
    ) -> list[dict]:
        return self.repo.get_top_related_products(
            tenant_id=tenant_id,
            product_id=product_id,
            limit=limit,
        )