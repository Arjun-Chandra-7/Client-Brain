from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Client, Constraint, Goal, SocialAccount, Source, SourceType
from app.repositories.client_repository import ClientRepository
from app.schemas import BootstrapRequest, ClientCreate, FactCreate
from app.services.fact_service import FactService
from app.services.research_service import ResearchProvider, UnavailableResearchProvider


class ClientService:
    def __init__(self, db: Session, research: ResearchProvider | None = None):
        self.db, self.repo, self.facts, self.research = db, ClientRepository(db), FactService(db), research or UnavailableResearchProvider()

    def create(self, payload: ClientCreate) -> Client:
        return self.repo.create(Client(name=payload.name, business_name=payload.business_name, website=payload.website))

    def bootstrap(self, client: Client, payload: BootstrapRequest) -> dict:
        input_source = Source(client_id=client.id, source_type=SourceType.CLIENT_INPUT, title="Bootstrap client input", raw_reference=payload.notes)
        self.db.add(input_source); self.db.flush()
        source_ids = [input_source.id]
        inputs = [("identity", "client_name", payload.name), ("business", "business_name", payload.business_name),
                  ("business", "website", payload.website), ("niche", "primary_niche", payload.niche)]
        for category, key, value in inputs:
            if value: self.facts.add(client, FactCreate(category=category, key=key, value=value, fact_type="client_provided", confidence=0.9, source_ids=source_ids))
        if payload.notes:
            self.facts.add(client, FactCreate(category="client_input", key="notes", value=payload.notes, fact_type="client_provided", confidence=0.7, source_ids=source_ids))
        for document in payload.documents:
            source = Source(client_id=client.id, source_type=SourceType.DOCUMENT, title="Pasted document", raw_reference=document)
            self.db.add(source); self.db.flush()
            self.facts.add(client, FactCreate(category="client_input", key="document_text", value=document, fact_type="client_provided", confidence=0.7, source_ids=[source.id]))
        for url in payload.social_links:
            account = SocialAccount(client_id=client.id, platform=self._platform(url), url=url)
            self.db.add(account)
            source = Source(client_id=client.id, source_type=SourceType.SOCIAL, url=url, title="Client-provided social URL")
            self.db.add(source); self.db.flush()
            self.facts.add(client, FactCreate(category="social_presence", key="social_url", value=url, fact_type="client_provided", confidence=0.9, source_ids=[source.id]))
        for statement in payload.goals: self.db.add(Goal(client_id=client.id, statement=statement))
        for statement in payload.constraints: self.db.add(Constraint(client_id=client.id, statement=statement))
        self.db.commit()
        unavailable = [u for u in [payload.website, *payload.social_links] if u]
        missing = self.missing_information(client.id, research_unavailable=unavailable)
        return {"client": client, "missing_information": missing, "research_status": "not_collected_no_research_provider" if unavailable else "not_requested"}

    @staticmethod
    def _platform(url: str) -> str:
        for item in ("instagram", "linkedin", "youtube", "tiktok", "facebook", "x.com", "twitter"):
            if item in url.lower(): return item
        return "other"

    def missing_information(self, client_id: str, research_unavailable: list[str] | None = None) -> list[str]:
        facts = self.facts.active(client_id)
        categories = {f.category for f in facts}
        goals = list(self.db.scalars(select(Goal).where(Goal.client_id == client_id)))
        constraints = list(self.db.scalars(select(Constraint).where(Constraint.client_id == client_id)))
        if goals: categories.add("goals")
        if constraints: categories.add("constraints")

        required = {
            "offers": "offers/products/services",
            "audience": "target audience",
            "brand": "brand voice/personality",
            "competitors": "competitors",
            "goals": "goals",
            "constraints": "constraints"
        }
        missing = [label for category, label in required.items() if category not in categories]
        if research_unavailable:
            missing.append("website/social content has not been researched: configure a ResearchProvider")
        elif not missing:
            # If all core public categories are established, identify true internal gaps
            missing.append("private unit economics and internal profit margins")
            missing.append("internal customer lifetime value (LTV) and churn metrics")
            if "goals" not in categories and not goals:
                missing.append("internal campaign goals and stakeholder constraints")
        return missing
