# Client Brain V1

Client Brain is a standalone VIRALYST supporting agent that stores source-backed, updateable intelligence about a client. It is intentionally an evidence system, not a giant prompt or unstructured JSON document.

## What works now

- Create and bootstrap clients from identity, URLs, notes, pasted documents, goals, and constraints.
- Persist canonical records in SQLite through SQLAlchemy (the same models work with a PostgreSQL URL later).
- Store facts with a type (`client_provided`, `observed`, `measured`, `researched`, `inferred`, or `hypothesis`), confidence, lifecycle status, timestamps, and source links.
- Store sources separately from facts, preserving raw input/reference and provenance.
- Deduplicate identical evidence claims and supersede older active values without deleting history.
- Build structured client profiles, task-scoped context, and evidence-only question answers.
- Run without an LLM key or web research provider. In that mode URLs are retained, but never represented as researched.

## Architecture

`API -> services -> repositories/models -> SQLite`

The bootstrap pipeline is: normalize input -> create client -> retain client-input sources -> create source-backed facts -> deduplicate/version -> generate only provider-backed insights -> profile/context retrieval. `LLMProvider` and `ResearchProvider` are explicit extension boundaries; V1 defaults are safe no-ops.

Canonical tables: `clients`, `sources`, `facts`, `fact_sources`, `insights`, `insight_facts`, `insight_sources`, `offers`, `audience_segments`, `competitors`, `goals`, `constraints`, and `social_accounts`. Typed tables prepare future workflows; the fact ledger remains the evidence record.

## Install and run

```powershell
python -m pip install -r requirements.txt
python run.py
```

Open `http://127.0.0.1:8000/docs` for interactive API documentation. The default database is `data/client_brain.db`. Set `DATABASE_URL` to a PostgreSQL SQLAlchemy URL later; no service-layer rewrite is required.

## Example

```powershell
$client = Invoke-RestMethod -Method Post http://127.0.0.1:8000/clients -ContentType application/json -Body '{"name":"Alex Example","business_name":"Example Labs"}'
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/clients/$($client.id)/bootstrap" -ContentType application/json -Body '{"name":"Alex Example","business_name":"Example Labs","niche":"fitness coaching","notes":"Premium online coach"}'
Invoke-RestMethod "http://127.0.0.1:8000/clients/$($client.id)/profile"
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/clients/$($client.id)/context" -ContentType application/json -Body '{"task":"script_generation"}'
```

## Quick brand test (no code required)

Start the server and open `http://127.0.0.1:8010/research/test`. Enter a brand name (and ideally its official website). Client Brain will discover public web pages, save each page as a source, extract only published page claims as `researched` facts, then show the systematic profile. It cannot guarantee a search result is an official source, so supplying the official website gives the most reliable result. The host must allow outbound HTTPS access; otherwise the response explicitly reports `no_public_pages_retrieved` and you can still test with pasted notes/documents.

## API

`GET /health`; `POST,GET /clients`; `GET /clients/{id}`; `POST /clients/{id}/bootstrap`; `GET /clients/{id}/profile`; `GET,POST /clients/{id}/facts` (`include_history=true` exposes superseded facts); `GET,POST /clients/{id}/insights`; `POST /clients/{id}/sources`; `POST /clients/{id}/context`; `POST /clients/{id}/ask`; and `GET /research/status`.

## Future integration

Other VIRALYST agents should call `POST /clients/{id}/context` with `general`, `script_generation`, `video_editing`, `marketing`, or `competitor_research`, rather than receiving an entire profile. V2 should add a real vetted research provider, LLM extraction with schema validation, vector retrieval over raw documents, authenticated ownership, migrations, richer structured offer/audience CRUD, and measured content-performance insights.
