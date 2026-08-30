from pathlib import Path
from app.db.session import SessionLocal
from app.schemas import BrandAnalysisRequest
from app.services.brand_analysis_service import BrandAnalysisService
from app.services.export_service import YTExportService
from app.services.verification_service import FactVerificationService


def test_verification_service_audit(client):
    c_res = client.post("/clients", json={"name": "Test Co", "business_name": "Test Co", "website": "https://example.com"})
    cid = c_res.json()["id"]

    src_res = client.post(f"/clients/{cid}/sources", json={
        "source_type": "website",
        "url": "https://example.com",
        "title": "Example Domain",
        "raw_reference": "Example Domain is established for illustrative examples in documents."
    })
    sid = src_res.json()["id"]

    client.post(f"/clients/{cid}/facts", json={
        "category": "summary",
        "key": "purpose",
        "value": "illustrative examples in documents",
        "fact_type": "researched",
        "confidence": 0.9,
        "source_ids": [sid]
    })

    client.post(f"/clients/{cid}/facts", json={
        "category": "audience",
        "key": "target",
        "value": "developers and document writers",
        "fact_type": "researched",
        "confidence": 0.8,
        "source_ids": [sid]
    })

    # Run verification endpoint
    v_res = client.post(f"/clients/{cid}/verify", json={"check_live_urls": False})
    assert v_res.status_code == 200
    report = v_res.json()

    assert report["client_id"] == cid
    assert report["summary"]["total_facts"] == 2
    assert report["summary"]["grounded_facts"] >= 1
    assert report["overall_health_score"] > 50


def test_yt_searcher_export_endpoint(client, tmp_path):
    c_res = client.post("/clients", json={"name": "Alpha Corp", "business_name": "Alpha Corp", "website": "https://alpha.com"})
    cid = c_res.json()["id"]

    client.post(f"/clients/{cid}/facts", json={
        "category": "niche", "key": "primary_niche", "value": "fitness", "fact_type": "client_provided", "confidence": 0.9
    })
    client.post(f"/clients/{cid}/facts", json={
        "category": "niche", "key": "sub_niches", "value": ["calisthenics", "gymnastics"], "fact_type": "client_provided", "confidence": 0.9
    })
    client.post(f"/clients/{cid}/facts", json={
        "category": "offers", "key": "flagship_lines", "value": ["Coaching Plan", "App Subscription"], "fact_type": "client_provided", "confidence": 0.9
    })
    client.post(f"/clients/{cid}/facts", json={
        "category": "marketing_intelligence", "key": "content_pillars", "value": ["Skill Tutorials", "Diet Hacks"], "fact_type": "client_provided", "confidence": 0.9
    })

    # Test GET export
    export_res = client.get(f"/clients/{cid}/export/yt-searcher")
    assert export_res.status_code == 200
    yt_json = export_res.json()

    assert yt_json["business_name"] == "Alpha Corp"
    assert yt_json["primary_niche"] == "fitness"
    assert "calisthenics" in yt_json["subniches"]
    assert "Coaching Plan" in yt_json["products"]
    assert "Skill Tutorials" in yt_json["content_pillars"]

    # Test direct client.json alias
    alias_res = client.get(f"/clients/{cid}/client.json")
    assert alias_res.status_code == 200
    assert alias_res.json()["business_name"] == "Alpha Corp"

    # Test Save endpoint
    save_target = tmp_path / "client.json"
    save_res = client.post(f"/clients/{cid}/export/yt-searcher/save", json={"output_path": str(save_target)})
    assert save_res.status_code == 200
    assert save_target.exists()

    # Test default Client info folder save
    default_save_res = client.post(f"/clients/{cid}/export/yt-searcher/save")
    assert default_save_res.status_code == 200
    assert Path("Client info/client.json").exists()
    assert Path("Client info/Alpha_Corp.json").exists()
