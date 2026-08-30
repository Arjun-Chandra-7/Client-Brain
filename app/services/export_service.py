from __future__ import annotations

from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Client, Constraint, Goal, SocialAccount
from app.services.fact_service import FactService
from app.services.insight_service import InsightService


class YTExportService:
    """Exports structured, evidence-backed client profiles tailored for YT-Searcher consumption."""

    def __init__(self, db: Session):
        self.db = db
        self.facts = FactService(db)
        self.insights = InsightService(db)

    def build_client_json(self, client_id: str) -> dict[str, Any]:
        client = self.db.get(Client, client_id)
        if not client:
            raise ValueError(f"Client '{client_id}' not found")

        active_facts = self.facts.active(client_id)
        grouped: dict[str, dict[str, Any]] = {}
        for f in active_facts:
            grouped.setdefault(f.category, {})[f.key] = f.value_json

        goals = [g.statement for g in self.db.scalars(select(Goal).where(Goal.client_id == client_id))]
        constraints = [c.statement for c in self.db.scalars(select(Constraint).where(Constraint.client_id == client_id))]
        socials = [s.url for s in self.db.scalars(select(SocialAccount).where(SocialAccount.client_id == client_id))]

        def _as_list(val: Any) -> list[str]:
            if not val:
                return []
            if isinstance(val, list):
                out = []
                for item in val:
                    if isinstance(item, str):
                        out.append(item.strip())
                    elif isinstance(item, dict) and "name" in item:
                        out.append(str(item["name"]).strip())
                    elif isinstance(item, (int, float)):
                        out.append(str(item))
                return [x for x in out if x]
            if isinstance(val, str):
                return [x.strip() for x in val.split(",") if x.strip()] if "," in val else [val.strip()]
            return [str(val).strip()]

        identity = grouped.get("identity", {})
        niche = grouped.get("niche", {})
        offers = grouped.get("offers", {})
        audience = grouped.get("audience", {})
        brand = grouped.get("brand", {})
        competitors = grouped.get("competitors", {})
        marketing = grouped.get("marketing_intelligence", {})
        social_presence = grouped.get("social_presence", {})

        # Subniches & Categories
        subniches = _as_list(niche.get("sub_niches"))
        if not subniches and niche.get("market_category"):
            subniches.extend(_as_list(niche.get("market_category")))

        # Products & Services
        products = _as_list(offers.get("flagship_lines")) or _as_list(offers.get("major_offerings")) or _as_list(offers.get("product_categories"))

        # Target Audience & Personas
        target_audience = _as_list(audience.get("primary_customer_segments")) or _as_list(audience.get("demographics"))

        # Problems & Pain Points
        pain_points = _as_list(audience.get("customer_pain_points"))

        # Competitors & Creators
        competitor_list = _as_list(competitors.get("direct_competitors"))
        creators_list = _as_list(competitors.get("indirect_competitors"))

        # Content Pillars & Topics
        content_pillars = _as_list(marketing.get("content_pillars"))
        topics = _as_list(marketing.get("authoritative_topics"))
        keywords = _as_list(marketing.get("messaging_hooks")) or _as_list(marketing.get("customer_angles"))

        # Exclusions
        exclusions = _as_list(grouped.get("exclusions", {}).get("excluded_terms"))
        if not exclusions and constraints:
            exclusions = [c for c in constraints if any(neg in c.lower() for neg in ("no ", "never ", "avoid ", "exclude ", "do not"))]

        # Extract brand name and company details
        brand_name = client.business_name or client.name or identity.get("company_legal_name") or "client"
        founders = grouped.get("founder", {}).get("founders") or ""
        leadership = grouped.get("founder", {}).get("current_leadership_or_ceo") or ""
        founding = identity.get("founding_details") or grouped.get("business", {}).get("founding_claim") or ""
        headquarters = identity.get("headquarters") or ""
        business_model = grouped.get("business", {}).get("business_model") or "Commercial delivery & digital operations"
        revenue_scale = grouped.get("business", {}).get("revenue_scale") or grouped.get("business", {}).get("operational_scale") or ""
        exec_summary = grouped.get("summary", {}).get("executive_summary") or grouped.get("summary", {}).get("website_description_claim") or ""

        from app.services.verification_service import FactVerificationService
        verification_report = FactVerificationService(self.db).run_full_verification(client.id, check_live_urls=False, update_timestamps=False).to_dict()

        # Build clean, complete YT-Searcher contract
        client_json: dict[str, Any] = {
            "client_id": client.id,
            "business_name": brand_name,
            "company_name": identity.get("company_legal_name") or brand_name,
            "client_name": client.name,
            "website": client.website or identity.get("official_website"),
            "industry": identity.get("industry") or niche.get("primary_niche") or "General Business",
            "primary_niche": niche.get("primary_niche") or identity.get("industry") or "General",
            "subniches": subniches,
            "company_overview": {
                "legal_name": identity.get("company_legal_name") or brand_name,
                "founders": founders,
                "leadership": leadership,
                "founding_details": founding,
                "headquarters": headquarters,
                "business_model": business_model,
                "revenue_scale": revenue_scale,
                "executive_summary": exec_summary
            },
            "products": products,
            "target_audience": target_audience,
            "audience_problems": pain_points,
            "pain_points": pain_points,
            "content_pillars": content_pillars,
            "topics": topics,
            "keywords": keywords,
            "competitors": competitor_list,
            "creators": creators_list,
            "exclusions": exclusions,
            "languages": ["en"],
            "geographies": _as_list(identity.get("operating_markets")) or ["Global", "US"],
            "brand_positioning": brand.get("brand_positioning") or brand.get("unique_selling_proposition") or "",
            "tone_of_voice": brand.get("tone_of_voice") or brand.get("brand_personality") or "",
            "aspirations": goals,
            "goals": goals,
            "constraints": constraints,
            "social_links": socials,
            "_viralyst_metadata": {
                "source_system": "VIRALYST_Client_Brain_V1",
                "evidence_health_score": verification_report.get("overall_health_score", 100.0),
                "total_verified_facts": len(active_facts),
                "grounded_facts": verification_report.get("summary", {}).get("grounded_facts", len(active_facts)),
                "conflicts_count": verification_report.get("summary", {}).get("conflicts_count", 0),
                "verified_at": verification_report.get("verified_at"),
                "generated_at": client.updated_at.isoformat() if client.updated_at else None,
                "handoff_target": "https://github.com/Arjun-Chandra-7/YT-Searcher"
            }
        }

        return client_json

    def export_and_save(self, client_id: str, output_dir: str = "Client info") -> dict[str, Any]:
        data = self.build_client_json(client_id)
        saved_paths = self.save_client_info(data, output_dir=output_dir)
        data["_viralyst_saved_paths"] = saved_paths
        return data

    @staticmethod
    def save_client_info(client_json: dict[str, Any], output_dir: str = "Client info") -> dict[str, str]:
        import os
        import json
        import re

        os.makedirs(output_dir, exist_ok=True)
        brand_name = client_json.get("company_name") or client_json.get("business_name") or client_json.get("client_name") or "client"
        safe_name = re.sub(r"[^a-zA-Z0-9_\- ]", "", brand_name).strip().replace(" ", "_")
        if not safe_name:
            safe_name = "client"

        latest_path = os.path.join(output_dir, "client.json")
        named_path = os.path.join(output_dir, f"{safe_name}.json")

        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(client_json, f, indent=2, ensure_ascii=False)

        with open(named_path, "w", encoding="utf-8") as f:
            json.dump(client_json, f, indent=2, ensure_ascii=False)

        return {
            "latest_file": latest_path,
            "named_file": named_path,
            "directory": output_dir
        }
