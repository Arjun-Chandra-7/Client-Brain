from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Fact, Insight, RecordStatus, Source
from app.schemas import InsightCreate


class InsightService:
    def __init__(self, db: Session): self.db = db
    def list(self, client_id: str) -> list[Insight]:
        return list(self.db.scalars(select(Insight).where(Insight.client_id == client_id, Insight.status == RecordStatus.ACTIVE)))
    def add(self, client_id: str, payload: InsightCreate) -> Insight:
        facts = list(self.db.scalars(select(Fact).where(Fact.client_id == client_id, Fact.id.in_(payload.supporting_fact_ids))))
        sources = list(self.db.scalars(select(Source).where(Source.client_id == client_id, Source.id.in_(payload.supporting_source_ids)))) if payload.supporting_source_ids else []
        if len(facts) != len(set(payload.supporting_fact_ids)) or len(sources) != len(set(payload.supporting_source_ids)):
            raise ValueError("Every supporting fact/source must belong to this client")
        insight = Insight(client_id=client_id, statement=payload.statement, category=payload.category, confidence=payload.confidence,
                          sample_size=payload.sample_size, date_range=payload.date_range, supporting_facts=facts, supporting_sources=sources)
        self.db.add(insight); self.db.commit(); self.db.refresh(insight); return insight
    def generate_initial(self, client_id: str) -> list[Insight]:
        # Offline V1 deliberately makes no generated inferences. LLM-backed generation belongs behind LLMProvider.
        return self.list(client_id)
