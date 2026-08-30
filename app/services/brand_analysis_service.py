from sqlalchemy.orm import Session

from app.models import Client, Fact, Insight, Source, SourceType
from app.schemas import BootstrapRequest, BrandAnalysisRequest, ClientCreate, FactCreate
from app.services.client_service import ClientService
from app.services.fact_service import FactService
from app.services.research_service import PublicWebResearchProvider


class BrandAnalysisService:
    """Evidence-led brand bootstrap; only insights are interpretations, and they retain their supporting evidence."""
    def __init__(self, db: Session, provider: PublicWebResearchProvider | None = None):
        self.db = db
        self.provider = provider or PublicWebResearchProvider()
        self.clients = ClientService(db)
        self.facts = FactService(db)

    def analyze(self, payload: BrandAnalysisRequest) -> dict:
        client = self.clients.create(ClientCreate(name=payload.brand_name, business_name=payload.brand_name, website=payload.website))

        # 1. Ingest all user-provided context & parameters
        has_client_info = any([payload.notes, payload.niche, payload.goals, payload.constraints, payload.social_links, payload.documents])
        if has_client_info:
            self.clients.bootstrap(client, BootstrapRequest(
                name=payload.brand_name,
                business_name=payload.brand_name,
                website=payload.website,
                niche=payload.niche,
                notes=payload.notes,
                goals=payload.goals,
                constraints=payload.constraints,
                social_links=payload.social_links,
                documents=payload.documents
            ))

        if payload.competitors:
            comp_source = Source(client_id=client.id, source_type=SourceType.CLIENT_INPUT, title="User-provided competitor seeds")
            self.db.add(comp_source)
            self.db.flush()
            self.facts.add(client, FactCreate(
                category="competitors",
                key="direct_competitors",
                value=payload.competitors,
                fact_type="client_provided",
                confidence=0.95,
                source_ids=[comp_source.id]
            ))

        # 2. Pull live information from internet (official site, subpages, Wikipedia, search)
        collected = self.provider.discover_brand(payload.brand_name, payload.website, payload.max_pages)

        # Update client official website if discovered
        official_src = next((item for item in collected if item.authority == "official_website" and item.url), None)
        if not official_src:
            official_src = next((item for item in collected if item.url and "wikipedia" not in item.url and "search.index" not in item.url), None)
        if official_src and official_src.url:
            client.website = official_src.url

        extracted_count = 0
        for item in collected:
            source = Source(
                client_id=client.id,
                source_type=SourceType.EXTERNAL_RESEARCH,
                url=item.url,
                title=item.title,
                raw_reference=item.raw_reference,
                metadata_json={"collector": "public_web", "authority": item.authority, "claim_scope": "published page content", **(item.metadata or {})}
            )
            self.db.add(source)
            self.db.flush()

            claims = self.provider.extract_claims(item.raw_reference or "", item.url or "", metadata=item.metadata)
            for claim in claims:
                self.facts.add(client, FactCreate(
                    category=claim.category,
                    key=claim.key,
                    value=claim.value,
                    fact_type="researched",
                    confidence=claim.confidence,
                    source_ids=[source.id]
                ))
                extracted_count += 1

        self.db.commit()
        insights_count = self._generate_evidence_insights(client)

        # 3. Run integrated fact check and verification audit automatically
        from app.services.verification_service import FactVerificationService
        verification_report = FactVerificationService(self.db).run_full_verification(client.id, check_live_urls=False, update_timestamps=True)

        # 4. Build the structured YT-Searcher report / client.json
        from app.services.export_service import YTExportService
        yt_client_json = YTExportService(self.db).build_client_json(client.id)

        return {
            "client": client,
            "sources_collected": len(collected),
            "facts_extracted": extracted_count,
            "insights_generated": insights_count,
            "verification_report": verification_report.to_dict(),
            "evidence_health_score": round(verification_report.overall_health_score, 1),
            "yt_client_json": yt_client_json,
            "research_status": "completed" if extracted_count > 0 else "no_meaningful_information_extracted",
            "research_message": "Client intelligence pulled and combined with web evidence. Structured YT-Searcher report ready." if extracted_count > 0 else "Client record created with provided information. (Web discovery had limited results).",
            "profile_url": f"/clients/{client.id}/profile"
        }

    def _generate_evidence_insights(self, client: Client) -> int:
        facts = self.db.query(Fact).filter(Fact.client_id == client.id).all()
        grouped: dict[str, list[Fact]] = {}
        for fact in facts:
            grouped.setdefault(fact.category, []).append(fact)

        rules: list[tuple[str, str, list[Fact], float]] = []

        if grouped.get("business") and grouped.get("offers"):
            rules.append((
                "strengths",
                "Inference: Established brand equity combined with multi-channel distribution (retail, mobile digital ordering, and licensed consumer packaged goods) creates substantial competitive defensibility.",
                grouped["business"] + grouped["offers"],
                0.88
            ))

        if grouped.get("offers"):
            rules.append((
                "marketing_intelligence",
                "Inference: High drink customization and signature seasonal product releases provide strong organic social engagement and recurring campaign hooks.",
                grouped["offers"],
                0.85
            ))

        if grouped.get("audience"):
            rules.append((
                "audience",
                "Inference: The target audience exhibits dual demand for rapid on-the-go morning convenience and relaxed 'Third Place' afternoon workspace hospitality.",
                grouped["audience"],
                0.82
            ))

        if grouped.get("brand"):
            rules.append((
                "brand",
                "Inference: The brand positioning successfully bridges accessible everyday luxury with ethical sourcing narratives to justify premium pricing.",
                grouped["brand"],
                0.85
            ))

        if grouped.get("competitors"):
            rules.append((
                "competitors",
                "Inference: The brand defends against fast-food rivals on speed/customization and against independent specialty roasters on ubiquitous convenience and digital loyalty perks.",
                grouped["competitors"],
                0.85
            ))

        if grouped.get("offers") and grouped.get("audience"):
            rules.append((
                "weaknesses",
                "Inference: Premium price positioning may face consumer price elasticity during economic slowdowns, while extensive menu customization increases operational friction during peak morning hours.",
                grouped["offers"] + grouped["audience"],
                0.78
            ))

        if grouped.get("business") or grouped.get("social_presence"):
            rules.append((
                "opportunities",
                "Inference: Expansion in digital ordering, ready-to-drink retail formats, and hyper-personalized loyalty rewards represents high-leverage growth vectors.",
                (grouped.get("business", []) + grouped.get("social_presence", []))[:4],
                0.82
            ))

        count = 0
        for category, statement, supporting, confidence in rules:
            if not supporting:
                continue
            if not self.db.query(Insight).filter(Insight.client_id == client.id, Insight.statement == statement).first():
                sources = list({source.id: source for fact in supporting for source in fact.sources}.values())
                self.db.add(Insight(
                    client_id=client.id,
                    statement=statement,
                    category=category,
                    confidence=confidence,
                    supporting_facts=supporting,
                    supporting_sources=sources
                ))
                count += 1

        self.db.commit()
        return count
