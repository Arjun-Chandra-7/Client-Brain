def make_client(client):
    response = client.post("/clients", json={"name": "Alex Example", "business_name": "Example Labs", "website": "https://example.com"})
    assert response.status_code == 201
    return response.json()["id"]


def test_bootstrap_profile_provenance_and_missing_information(client):
    client_id = make_client(client)
    response = client.post(f"/clients/{client_id}/bootstrap", json={
        "name": "Alex Example", "business_name": "Example Labs", "website": "https://example.com",
        "niche": "fitness coaching", "notes": "Premium online fitness coach.",
        "social_links": ["https://instagram.com/alexexample"], "goals": ["Generate qualified leads"],
    })
    assert response.status_code == 200
    assert response.json()["research_status"] == "not_collected_no_research_provider"
    profile = client.get(f"/clients/{client_id}/profile").json()
    assert profile["niche"][0]["value"] == "fitness coaching"
    assert profile["niche"][0]["fact_type"] == "client_provided"
    assert profile["facts"][0]["source_ids"]
    assert "offers/products/services" in profile["missing_information"]


def test_fact_deduplication_and_superseding_preserves_history(client):
    client_id = make_client(client)
    source = client.post(f"/clients/{client_id}/sources", json={"source_type": "client_input", "title": "Rate card"}).json()
    fact = {"category": "offers", "key": "price", "value": 9999, "fact_type": "client_provided", "confidence": .9, "source_ids": [source["id"]]}
    first = client.post(f"/clients/{client_id}/facts", json=fact)
    duplicate = client.post(f"/clients/{client_id}/facts", json=fact)
    assert first.json()["id"] == duplicate.json()["id"]
    replacement = client.post(f"/clients/{client_id}/facts", json={**fact, "value": 14999, "supersede_existing": True})
    assert replacement.status_code == 201
    active = client.get(f"/clients/{client_id}/facts").json()
    assert len(active) == 1 and active[0]["value"] == 14999
    history = client.get(f"/clients/{client_id}/facts?include_history=true").json()
    assert {item["status"] for item in history} == {"active", "superseded"}


def test_task_context_filters_unrelated_facts(client):
    client_id = make_client(client)
    for payload in [
        {"category": "audience", "key": "pain", "value": "lack of time", "fact_type": "client_provided", "confidence": .8},
        {"category": "creative", "key": "caption_style", "value": "minimal", "fact_type": "client_provided", "confidence": .8},
    ]: assert client.post(f"/clients/{client_id}/facts", json=payload).status_code == 201
    result = client.post(f"/clients/{client_id}/context", json={"task": "script_generation"}).json()
    assert [f["category"] for f in result["facts"]] == ["audience"]


def test_insight_requires_and_preserves_evidence_linkage(client):
    client_id = make_client(client)
    fact = client.post(f"/clients/{client_id}/facts", json={"category": "content", "key": "hook", "value": "contrarian", "fact_type": "measured", "confidence": .8}).json()
    insight = client.post(f"/clients/{client_id}/insights", json={"statement": "Contrarian hooks may be effective.", "category": "content_performance", "confidence": .6, "supporting_fact_ids": [fact["id"]]} )
    assert insight.status_code == 201
    assert insight.json()["supporting_fact_ids"] == [fact["id"]]


def test_question_unknown_is_explicit(client):
    client_id = make_client(client)
    answer = client.post(f"/clients/{client_id}/ask", json={"question": "What is the preferred content tone?"}).json()
    assert answer["known_facts"] == []
    assert answer["unknown"] == ["What is the preferred content tone?"]
    assert answer["answer"].startswith("Unknown")


def test_public_page_extraction_is_source_claim_oriented():
    from app.services.research_service import PublicWebResearchProvider
    page = '''<html><head><title>Acme - Better Widgets</title><meta name="description" content="Acme says it makes durable widgets."></head><body><h1>Widgets for teams</h1><script type="application/ld+json">{"name":"Acme","foundingDate":"2015"}</script></body></html>'''
    claims = PublicWebResearchProvider.extract_claims(page)
    assert any(c.key == "website_description_claim" and "Acme says" in c.value for c in claims)
    assert any(c.key == "structured_data_foundingDate" and c.value == "2015" for c in claims)


def test_google_redirect_is_resolved_before_research():
    from app.services.research_service import PublicWebResearchProvider
    assert PublicWebResearchProvider.normalize_url("https://www.google.com/url?q=https%3A%2F%2Fwww.example.com%2Fabout") == "https://www.example.com/about"
