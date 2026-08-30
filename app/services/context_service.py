from sqlalchemy.orm import Session
from app.models import Constraint, Goal, SocialAccount
from app.services.fact_service import FactService
from app.services.insight_service import InsightService


TASK_CATEGORIES = {
    "general": {"identity", "business", "niche", "offers", "audience", "brand", "social_presence", "competitors", "goals", "constraints"},
    "script_generation": {"audience", "offers", "brand", "positioning", "constraints", "content", "niche"},
    "video_editing": {"brand", "creative", "content", "constraints", "social_presence"},
    "marketing": {"offers", "audience", "positioning", "competitors", "brand", "goals", "niche"},
    "competitor_research": {"competitors", "niche", "audience", "positioning", "offers"},
}


class ContextService:
    def __init__(self, db: Session): self.db, self.facts, self.insights = db, FactService(db), InsightService(db)
    def get_context(self, client_id: str, task: str) -> dict:
        if task not in TASK_CATEGORIES: raise ValueError(f"Unsupported task '{task}'")
        facts = self.facts.active(client_id, TASK_CATEGORIES[task])
        return {"task": task, "facts": facts, "insights": self.insights.list(client_id),
                "goals": list(self.db.scalars(__import__('sqlalchemy').select(Goal).where(Goal.client_id == client_id))),
                "constraints": list(self.db.scalars(__import__('sqlalchemy').select(Constraint).where(Constraint.client_id == client_id)))}
