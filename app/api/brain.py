from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.dependencies import client_or_404
from app.api.serializers import fact_out, insight_out
from app.db.session import get_db
from app.models import Client
from app.schemas import AskRequest, ContextRequest
from app.services.context_service import ContextService

router = APIRouter(prefix="/clients", tags=["brain"])


@router.post("/{client_id}/context")
def context(payload: ContextRequest, client: Client = Depends(client_or_404), db: Session = Depends(get_db)):
    try: result = ContextService(db).get_context(client.id, payload.task)
    except ValueError as error: raise HTTPException(422, str(error))
    return {"task": result["task"], "facts": [fact_out(f) for f in result["facts"]], "insights": [insight_out(i) for i in result["insights"]],
            "goals": [g.statement for g in result["goals"]], "constraints": [c.statement for c in result["constraints"]]}


@router.post("/{client_id}/ask")
def ask(payload: AskRequest, client: Client = Depends(client_or_404), db: Session = Depends(get_db)):
    # Retrieval is deliberately lexical in V1; no question is answered without persisted evidence.
    result = ContextService(db).get_context(client.id, "general")
    terms = {word.lower().strip("?.,!") for word in payload.question.split() if len(word) > 2}
    facts = [f for f in result["facts"] if terms & set((f.category + " " + f.key + " " + str(f.value_json)).lower().split())]
    insights = [i for i in result["insights"] if terms & set((i.category + " " + i.statement).lower().split())]
    if facts or insights:
        answer = "Retrieved persisted evidence relevant to the question. Facts and inferences are separated below."
        unknown = []
    else:
        answer = "Unknown: Client Brain has no stored evidence sufficient to answer this question."
        unknown = [payload.question]
    return {"known_facts": [fact_out(f) for f in facts], "inferences": [insight_out(i) for i in insights], "unknown": unknown, "answer": answer}
