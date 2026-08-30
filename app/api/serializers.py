from app.models import Fact, Insight, Source


def fact_out(fact: Fact) -> dict:
    return {"id": fact.id, "category": fact.category, "key": fact.key, "value": fact.value_json,
            "fact_type": fact.fact_type, "confidence": fact.confidence, "status": fact.status,
            "source_ids": [s.id for s in fact.sources], "created_at": fact.created_at, "updated_at": fact.updated_at,
            "last_verified_at": fact.last_verified_at}


def source_out(source: Source) -> dict:
    return {"id": source.id, "source_type": source.source_type, "url": source.url, "title": source.title,
            "raw_reference": source.raw_reference, "captured_at": source.captured_at, "metadata": source.metadata_json}


def insight_out(insight: Insight) -> dict:
    return {"id": insight.id, "statement": insight.statement, "category": insight.category, "confidence": insight.confidence,
            "status": insight.status, "supporting_fact_ids": [f.id for f in insight.supporting_facts],
            "supporting_source_ids": [s.id for s in insight.supporting_sources]}
