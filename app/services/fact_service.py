from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Client, Fact, FactType, RecordStatus, Source
from app.schemas import FactCreate


class FactService:
    def __init__(self, db: Session): self.db = db

    def add(self, client: Client, payload: FactCreate) -> Fact:
        sources = list(self.db.scalars(select(Source).where(Source.client_id == client.id, Source.id.in_(payload.source_ids)))) if payload.source_ids else []
        if len(sources) != len(set(payload.source_ids)):
            raise ValueError("Every source_id must belong to this client")
        existing = list(self.db.scalars(select(Fact).where(Fact.client_id == client.id, Fact.category == payload.category, Fact.key == payload.key, Fact.status == RecordStatus.ACTIVE)))
        for fact in existing:
            if fact.value_json == payload.value and fact.fact_type == payload.fact_type:
                # Idempotent ingestion: add missing provenance without duplicating the claim.
                fact.sources = list({s.id: s for s in [*fact.sources, *sources]}.values())
                self.db.commit(); self.db.refresh(fact); return fact
        if existing and payload.supersede_existing:
            for fact in existing: fact.status = RecordStatus.SUPERSEDED
        fact = Fact(client_id=client.id, category=payload.category, key=payload.key, value_json=payload.value,
                    fact_type=payload.fact_type, confidence=payload.confidence, sources=sources)
        self.db.add(fact); self.db.commit(); self.db.refresh(fact); return fact

    def active(self, client_id: str, categories: set[str] | None = None) -> list[Fact]:
        query = select(Fact).where(Fact.client_id == client_id, Fact.status == RecordStatus.ACTIVE)
        if categories: query = query.where(Fact.category.in_(categories))
        return list(self.db.scalars(query.order_by(Fact.category, Fact.key)))

    def all(self, client_id: str) -> list[Fact]:
        return list(self.db.scalars(select(Fact).where(Fact.client_id == client_id).order_by(Fact.created_at)))
