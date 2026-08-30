from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.dependencies import client_or_404
from app.api.serializers import fact_out, insight_out, source_out
from app.db.session import get_db
from app.models import Client, Constraint, Goal, SocialAccount, Source
from app.schemas import BootstrapRequest, ClientCreate, FactCreate, InsightCreate, SourceCreate
from app.services.client_service import ClientService
from app.services.fact_service import FactService
from app.services.insight_service import InsightService

router = APIRouter(prefix="/clients", tags=["clients"])


def client_out(c: Client) -> dict:
    return {"id": c.id, "name": c.name, "business_name": c.business_name, "website": c.website, "status": c.status,
            "created_at": c.created_at, "updated_at": c.updated_at}


@router.post("", status_code=status.HTTP_201_CREATED)
def create(payload: ClientCreate, db: Session = Depends(get_db)):
    return client_out(ClientService(db).create(payload))


@router.get("")
def list_clients(db: Session = Depends(get_db)):
    return [client_out(c) for c in ClientService(db).repo.list()]


@router.get("/{client_id}")
def get(client: Client = Depends(client_or_404)): return client_out(client)


@router.post("/{client_id}/bootstrap")
def bootstrap(payload: BootstrapRequest, client: Client = Depends(client_or_404), db: Session = Depends(get_db)):
    result = ClientService(db).bootstrap(client, payload)
    return {"client": client_out(client), "research_status": result["research_status"], "missing_information": result["missing_information"]}


@router.post("/{client_id}/sources", status_code=status.HTTP_201_CREATED)
def add_source(payload: SourceCreate, client: Client = Depends(client_or_404), db: Session = Depends(get_db)):
    source = Source(client_id=client.id, source_type=payload.source_type, url=payload.url, title=payload.title,
                    raw_reference=payload.raw_reference, metadata_json=payload.metadata)
    db.add(source); db.commit(); db.refresh(source); return source_out(source)


@router.post("/{client_id}/facts", status_code=status.HTTP_201_CREATED)
def add_fact(payload: FactCreate, client: Client = Depends(client_or_404), db: Session = Depends(get_db)):
    try: return fact_out(FactService(db).add(client, payload))
    except ValueError as error: raise HTTPException(422, str(error))


@router.get("/{client_id}/facts")
def facts(include_history: bool = Query(False), client: Client = Depends(client_or_404), db: Session = Depends(get_db)):
    service = FactService(db)
    return [fact_out(f) for f in (service.all(client.id) if include_history else service.active(client.id))]


@router.get("/{client_id}/insights")
def insights(client: Client = Depends(client_or_404), db: Session = Depends(get_db)):
    return [insight_out(i) for i in InsightService(db).list(client.id)]


@router.post("/{client_id}/insights", status_code=status.HTTP_201_CREATED)
def add_insight(payload: InsightCreate, client: Client = Depends(client_or_404), db: Session = Depends(get_db)):
    try: return insight_out(InsightService(db).add(client.id, payload))
    except ValueError as error: raise HTTPException(422, str(error))


@router.get("/{client_id}/profile")
def profile(client: Client = Depends(client_or_404), db: Session = Depends(get_db)):
    fact_service = FactService(db)
    all_facts = fact_service.active(client.id)
    grouped = {}
    for fact in all_facts: grouped.setdefault(fact.category, []).append(fact_out(fact))
    service = ClientService(db)
    return {"client": client_out(client), "identity": grouped.get("identity", []), "business": grouped.get("business", []),
            "founder": grouped.get("founder", []) + grouped.get("key_people", []), "niche": grouped.get("niche", []), "offers": grouped.get("offers", []),
            "audience": grouped.get("audience", []), "brand": grouped.get("brand", []) + grouped.get("positioning", []),
            "social_presence": grouped.get("social_presence", []), "competitors": grouped.get("competitors", []),
            "summary": grouped.get("summary", []), "marketing_intelligence": grouped.get("marketing_intelligence", []),
            "goals": [g.statement for g in db.scalars(select(Goal).where(Goal.client_id == client.id))],
            "constraints": [c.statement for c in db.scalars(select(Constraint).where(Constraint.client_id == client.id))],
            "facts": [fact_out(f) for f in all_facts], "insights": [insight_out(i) for i in InsightService(db).list(client.id)],
            "sources": [source_out(s) for s in db.scalars(select(Source).where(Source.client_id == client.id))],
            "missing_information": service.missing_information(client.id)}
