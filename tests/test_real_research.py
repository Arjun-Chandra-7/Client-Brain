import pytest
from app.db.session import SessionLocal
from app.schemas import BrandAnalysisRequest
from app.services.brand_analysis_service import BrandAnalysisService
from app.services.fact_service import FactService
from app.services.insight_service import InsightService
from app.services.research_service import PublicWebResearchProvider


def test_google_redirect_normalization():
    url = "https://www.google.com/url?q=https%3A%2F%2Fwww.starbucks.com%2Fmenu&sa=D&sntz=1&usg=AOvVaw2"
    normalized = PublicWebResearchProvider.normalize_url(url)
    assert normalized == "https://www.starbucks.com/menu"

    # Search URL itself should not be treated as client website
    assert PublicWebResearchProvider.normalize_url("https://www.google.com/search?q=starbucks") is None


def test_starbucks_public_research_returns_full_analysis():
    db = SessionLocal()
    service = BrandAnalysisService(db)
    result = service.analyze(BrandAnalysisRequest(brand_name="Starbucks"))

    assert result["research_status"] == "completed"
    assert result["sources_collected"] > 0
    assert result["facts_extracted"] >= 15
    assert result["insights_generated"] >= 3

    fact_service = FactService(db)
    facts = fact_service.active(result["client"].id)
    categories = {f.category for f in facts}

    # Verify all major required sections are present
    assert "identity" in categories
    assert "business" in categories
    assert "niche" in categories
    assert "offers" in categories
    assert "audience" in categories
    assert "brand" in categories
    assert "competitors" in categories
    assert "marketing_intelligence" in categories
    assert "social_presence" in categories

    # Verify separate facts and source linkages
    for fact in facts:
        assert fact.confidence > 0
        assert fact.fact_type.value in {"researched", "client_provided"}
        assert len(fact.sources) > 0

    # Verify insights are evidence-linked
    insight_service = InsightService(db)
    insights = insight_service.list(result["client"].id)
    assert len(insights) >= 3
    for insight in insights:
        assert insight.statement.startswith("Inference:")
        assert len(insight.supporting_facts) > 0
        assert len(insight.supporting_sources) > 0


def test_smaller_business_research():
    db = SessionLocal()
    service = BrandAnalysisService(db)
    result = service.analyze(BrandAnalysisRequest(brand_name="Basecamp"))

    assert result["research_status"] == "completed"
    assert result["sources_collected"] > 0
    assert result["facts_extracted"] >= 5
    assert result["insights_generated"] >= 2

    facts = FactService(db).active(result["client"].id)
    categories = {f.category for f in facts}
    assert "niche" in categories
    assert "brand" in categories
    assert "audience" in categories
