from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.api.clients import client_out
from app.db.session import get_db
from app.schemas import BrandAnalysisRequest
from app.services.brand_analysis_service import BrandAnalysisService

router = APIRouter(prefix="/research", tags=["research"])


@router.get("/status")
def status():
    return {
        "provider": "public_web",
        "message": "Public search, Wikipedia knowledge extraction, and multi-source brand research are enabled."
    }


@router.post("/analyze")
def analyze_brand(payload: BrandAnalysisRequest, db: Session = Depends(get_db)):
    result = BrandAnalysisService(db).analyze(payload)
    return {
        "client": client_out(result["client"]),
        "sources_collected": result["sources_collected"],
        "facts_extracted": result["facts_extracted"],
        "insights_generated": result["insights_generated"],
        "research_status": result["research_status"],
        "research_message": result["research_message"],
        "profile_url": f"/clients/{result['client'].id}/profile"
    }


@router.get("/test", response_class=HTMLResponse, include_in_schema=False)
def test_page():
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>VIRALYST Client Brain | Intelligence & Fact Verification</title>
<style>
:root {
  --primary: #0f62fe;
  --primary-hover: #0353e9;
  --bg: #0f172a;
  --surface: #1e293b;
  --surface-alt: #334155;
  --text: #f8fafc;
  --text-muted: #94a3b8;
  --border: #334155;
  --card-border: #475569;
  --accent: #38bdf8;
  --success: #22c55e;
  --success-bg: rgba(34, 197, 94, 0.15);
  --warning: #f59e0b;
  --warning-bg: rgba(245, 158, 11, 0.15);
  --danger: #ef4444;
  --danger-bg: rgba(239, 68, 68, 0.15);
  --purple: #a855f7;
  --purple-bg: rgba(168, 85, 247, 0.15);
}
* { box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 20px 80px;
  color: var(--text);
  background: var(--bg);
  line-height: 1.5;
}
header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border);
}
.brand-title {
  display: flex;
  align-items: center;
  gap: 12px;
}
.brand-logo {
  background: linear-gradient(135deg, var(--primary), #8b5cf6);
  color: #fff;
  font-weight: 800;
  font-size: 18px;
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}
h1 {
  font-size: 24px;
  font-weight: 700;
  margin: 0;
  letter-spacing: -0.5px;
}
p.subtitle {
  color: var(--text-muted);
  margin: 2px 0 0;
  font-size: 13.5px;
}
.nav-links {
  display: flex;
  gap: 10px;
}
.nav-btn {
  background: var(--surface);
  color: var(--text-muted);
  border: 1px solid var(--border);
  padding: 8px 14px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  text-decoration: none;
  transition: all 0.15s ease;
}
.nav-btn:hover, .nav-btn.active {
  background: var(--primary);
  color: #fff;
  border-color: var(--primary);
}
.card {
  background: var(--surface);
  border: 1px solid var(--card-border);
  border-radius: 12px;
  padding: 22px;
  margin-bottom: 20px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
@media (max-width: 768px) {
  .grid { grid-template-columns: 1fr; }
}
.form-group {
  margin-bottom: 14px;
}
label {
  display: block;
  font-weight: 600;
  font-size: 13px;
  margin-bottom: 6px;
  color: #cbd5e1;
}
input, textarea {
  width: 100%;
  padding: 11px 14px;
  background: #0f172a;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 14px;
  color: #f8fafc;
  outline: none;
  transition: border-color 0.15s ease;
  font-family: inherit;
}
input:focus, textarea:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2);
}
.btn-group {
  display: flex;
  gap: 10px;
  margin-top: 14px;
}
button.btn {
  background: var(--primary);
  color: #ffffff;
  border: 0;
  border-radius: 8px;
  padding: 11px 20px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
button.btn:hover { background: var(--primary-hover); }
button.btn-secondary { background: var(--surface-alt); }
button.btn-secondary:hover { background: #475569; }
button.btn-success { background: #16a34a; }
button.btn-success:hover { background: #15803d; }
button.btn-warning { background: #d97706; }
button.btn-warning:hover { background: #b45309; }
button:disabled { background: #475569; color: #94a3b8; cursor: not-allowed; }

.tab-nav {
  display: flex;
  gap: 8px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 20px;
  padding-bottom: 10px;
}
.tab-link {
  background: transparent;
  color: var(--text-muted);
  border: none;
  font-size: 14px;
  font-weight: 600;
  padding: 8px 14px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.tab-link:hover { color: #f8fafc; background: rgba(255,255,255,0.05); }
.tab-link.active {
  color: #38bdf8;
  background: rgba(56, 189, 248, 0.12);
}

.fact-item {
  padding: 12px 0;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.fact-item:last-child { border-bottom: none; }
.fact-key {
  font-size: 11.5px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--accent);
  margin-bottom: 4px;
}
.fact-val {
  font-size: 14.5px;
  color: #f1f5f9;
  margin-bottom: 6px;
  word-break: break-word;
}
.fact-val ul { margin: 4px 0 0 18px; padding: 0; }
.meta-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  font-size: 11px;
}
.badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
  text-transform: uppercase;
  font-size: 10.5px;
  letter-spacing: 0.3px;
}
.badge-researched { background: var(--success-bg); color: #4ade80; border: 1px solid rgba(74, 222, 128, 0.3); }
.badge-inferred { background: var(--purple-bg); color: #c084fc; border: 1px solid rgba(192, 132, 252, 0.3); }
.badge-conf { background: rgba(255,255,255,0.08); color: #cbd5e1; }
.badge-cat { background: rgba(56, 189, 248, 0.12); color: #38bdf8; }
.badge-strong { background: var(--success-bg); color: #4ade80; }
.badge-moderate { background: var(--warning-bg); color: #fbbf24; }
.badge-weak { background: var(--danger-bg); color: #f87171; }

.insight-card {
  background: rgba(168, 85, 247, 0.08);
  border: 1px solid rgba(168, 85, 247, 0.25);
  border-radius: 8px;
  padding: 12px 14px;
  margin-bottom: 10px;
}
.insight-statement {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 6px;
  color: #f3e8ff;
}
.score-circle {
  font-size: 32px;
  font-weight: 800;
  display: flex;
  align-items: center;
  gap: 10px;
}
.score-val {
  padding: 4px 12px;
  border-radius: 8px;
}
.score-high { background: var(--success-bg); color: #4ade80; border: 1px solid #4ade80; }
.score-med { background: var(--warning-bg); color: #fbbf24; border: 1px solid #fbbf24; }
.score-low { background: var(--danger-bg); color: #f87171; border: 1px solid #f87171; }

.warn-box {
  background: var(--warning-bg);
  border: 1px solid var(--warning);
  color: #fde68a;
  padding: 14px;
  border-radius: 8px;
  margin-bottom: 16px;
}
.danger-box {
  background: var(--danger-bg);
  border: 1px solid var(--danger);
  color: #fecaca;
  padding: 14px;
  border-radius: 8px;
  margin-bottom: 16px;
}
.success-box {
  background: var(--success-bg);
  border: 1px solid var(--success);
  color: #bbf7d0;
  padding: 14px;
  border-radius: 8px;
  margin-bottom: 16px;
}
.loading-box {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-muted);
}
.spinner {
  border: 3px solid rgba(255,255,255,0.1);
  border-top: 3px solid var(--accent);
  border-radius: 50%;
  width: 32px;
  height: 32px;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 12px;
}
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
h2 {
  font-size: 17px;
  font-weight: 700;
  margin: 0 0 14px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
  color: #f8fafc;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
h2 .count {
  font-size: 12px;
  font-weight: normal;
  color: var(--text-muted);
}
.src-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.src-item {
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13.5px;
}
.src-item:last-child { border-bottom: none; }
.src-item a { color: var(--accent); text-decoration: none; font-weight: 500; }
.src-item a:hover { text-decoration: underline; }
pre {
  background: #090d16;
  color: #e2e8f0;
  padding: 14px;
  border-radius: 8px;
  overflow-x: auto;
  font-size: 12.5px;
  border: 1px solid #1e293b;
  max-height: 480px;
}
</style>
</head>
<body>

<header>
  <div class="brand-title">
    <div class="brand-logo">CB</div>
    <div>
      <h1>VIRALYST Client Brain</h1>
      <p class="subtitle">Evidence Ledger • Fact Checking & Verification • YT-Searcher Handoff</p>
    </div>
  </div>
  <div class="nav-links">
    <a href="/docs" target="_blank" class="nav-btn">API Docs (Swagger)</a>
    <a href="https://github.com/Arjun-Chandra-7/Client-Brain" target="_blank" class="nav-btn">GitHub Repo</a>
  </div>
</header>

<div class="tab-nav">
  <button class="tab-link active" onclick="switchTab('research')">🔍 Brand Research & Ingest</button>
  <button class="tab-link" onclick="switchTab('verifier')">🛡️ Fact Check & Verification Center</button>
  <button class="tab-link" onclick="switchTab('yt')">📦 YT-Searcher Export & Sync</button>
  <button class="tab-link" onclick="switchTab('ask')">💬 Evidence Q&A (/ask)</button>
</div>

<!-- TAB 1: RESEARCH -->
<div id="tab-research" class="tab-pane">
  <div class="card">
    <div class="grid">
      <div class="form-group">
        <label for="brand">Brand / Business Name *</label>
        <input id="brand" placeholder="e.g. Basecamp, Starbucks, Gymshark" value="Basecamp">
      </div>
      <div class="form-group">
        <label for="website">Official Website (optional / recommended)</label>
        <input id="website" placeholder="https://basecamp.com" value="https://basecamp.com">
      </div>
    </div>
    <div class="form-group">
      <label for="notes">Private Notes or Context (optional)</label>
      <textarea id="notes" rows="2" placeholder="Any internal background, target objectives, or constraints..."></textarea>
    </div>
    <div class="btn-group">
      <button id="submitBtn" class="btn" onclick="runResearch()">🚀 Research & Analyze Brand</button>
      <button class="btn btn-secondary" onclick="loadLatestProfile()">Load Current Active Profile</button>
    </div>
  </div>

  <div id="report"></div>
</div>

<!-- TAB 2: VERIFIER -->
<div id="tab-verifier" class="tab-pane" style="display:none;">
  <div class="card">
    <h2><span>🛡️ Fact Checking & Grounding Audit</span></h2>
    <p style="color:var(--text-muted);font-size:13.5px;margin:0 0 14px;">
      Verifies live HTTP source reachability, audits fact lexical grounding against source citations, detects contradictory claims, and validates evidence-backed insights.
    </p>
    <div class="btn-group">
      <button id="verifyBtn" class="btn btn-warning" onclick="runVerification(true)">🔍 Run Full Live Fact Check (with HTTP ping)</button>
      <button class="btn btn-secondary" onclick="runVerification(false)">Audit Against Cached Evidence</button>
    </div>
  </div>
  <div id="verifier-output"></div>
</div>

<!-- TAB 3: YT-SEARCHER -->
<div id="tab-yt" class="tab-pane" style="display:none;">
  <div class="card">
    <h2><span>📦 YT-Searcher Handoff (<a href="https://github.com/Arjun-Chandra-7/YT-Searcher" target="_blank" style="color:var(--accent)">Arjun-Chandra-7/YT-Searcher</a>)</span></h2>
    <p style="color:var(--text-muted);font-size:13.5px;margin:0 0 14px;">
      Formats the client's verified evidence ledger into the exact <code>client.json</code> contract consumed by YT-Searcher (for search planning, candidate expansion, and genome reranking).
    </p>
    <div class="btn-group">
      <button class="btn btn-success" onclick="syncToYTSearcher()">💾 Sync Directly to YT-Searcher (RAG/client.json)</button>
      <button class="btn btn-secondary" onclick="copyClientJson()">📋 Copy JSON</button>
      <button class="btn btn-secondary" onclick="downloadClientJson()">⬇️ Download client.json</button>
    </div>
  </div>
  <div id="yt-output"></div>
</div>

<!-- TAB 4: ASK -->
<div id="tab-ask" class="tab-pane" style="display:none;">
  <div class="card">
    <h2><span>💬 Evidence-Only Q&A Assistant</span></h2>
    <p style="color:var(--text-muted);font-size:13.5px;margin:0 0 14px;">
      Asks questions strictly against verified stored facts and inferences. Unknown answers are explicitly declared with zero hallucination.
    </p>
    <div class="form-group">
      <label for="askInput">Enter a question about the client/brand:</label>
      <input id="askInput" placeholder="e.g. What is the business model and target audience?" onkeydown="if(event.key==='Enter') runAsk()">
    </div>
    <button class="btn" onclick="runAsk()">Ask Client Brain</button>
  </div>
  <div id="ask-output"></div>
</div>

<script>
let currentClientId = null;
let currentClientJson = null;

function switchTab(tabId) {
  document.querySelectorAll('.tab-pane').forEach(el => el.style.display = 'none');
  document.querySelectorAll('.tab-link').forEach(el => el.classList.remove('active'));
  document.getElementById(`tab-${tabId}`).style.display = 'block';
  event.target.classList.add('active');

  if (tabId === 'yt' && currentClientId) loadYTJson();
  if (tabId === 'verifier' && currentClientId && !document.getElementById('verifier-output').innerHTML) runVerification(false);
}

const esc = s => String(s ?? '').replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));

function formatValue(v) {
  if (Array.isArray(v)) {
    return `<ul>${v.map(item => `<li>${esc(item)}</li>`).join('')}</ul>`;
  }
  if (typeof v === 'object' && v !== null) {
    return `<pre style="margin:4px 0;background:#090d16;padding:8px;">${esc(JSON.stringify(v, null, 2))}</pre>`;
  }
  return esc(v);
}

function renderFact(f) {
  const label = f.key.replace(/_/g, ' ');
  return `
    <div class="fact-item">
      <div class="fact-key">${esc(label)}</div>
      <div class="fact-val">${formatValue(f.value)}</div>
      <div class="meta-badges">
        <span class="badge badge-researched">${esc(f.fact_type)}</span>
        <span class="badge badge-conf">Conf: ${Math.round((f.confidence||0)*100)}%</span>
        <span class="badge badge-cat">${esc(f.category)}</span>
        ${f.source_ids?.length ? `<span class="badge" style="background:rgba(56,189,248,0.15);color:#38bdf8;">${f.source_ids.length} source(s)</span>` : ''}
      </div>
    </div>`;
}

function renderInsight(i) {
  return `
    <div class="insight-card">
      <div class="insight-statement">${esc(i.statement)}</div>
      <div class="meta-badges">
        <span class="badge badge-inferred">Inference</span>
        <span class="badge badge-cat">${esc(i.category)}</span>
        <span class="badge badge-conf">Conf: ${Math.round((i.confidence||0)*100)}%</span>
        <span class="badge" style="background:rgba(168,85,247,0.15);color:#c084fc;">${(i.supporting_fact_ids||[]).length} supporting fact(s)</span>
      </div>
    </div>`;
}

function renderSection(title, facts, insights = []) {
  if (!facts?.length && !insights?.length) return '';
  const total = (facts?.length || 0) + (insights?.length || 0);
  return `
    <section class="card">
      <h2><span>${title}</span> <span class="count">${total} item(s)</span></h2>
      ${(facts || []).map(renderFact).join('')}
      ${(insights || []).map(renderInsight).join('')}
    </section>`;
}

async function loadLatestProfile() {
  try {
    const res = await fetch('/clients');
    const clients = await res.json();
    if (!clients.length) {
      alert('No clients found. Run research first.');
      return;
    }
    const latest = clients[0];
    currentClientId = latest.id;
    const profRes = await fetch(`/clients/${latest.id}/profile`);
    const profile = await profRes.json();
    renderProfileView(profile, { research_status: 'loaded', sources_collected: profile.sources?.length||0, facts_extracted: profile.facts?.length||0, insights_generated: profile.insights?.length||0, research_message: 'Loaded active client intelligence from local database.' });
  } catch (err) {
    alert('Error loading profile: ' + err.message);
  }
}

async function runResearch() {
  const root = document.getElementById('report');
  const btn = document.getElementById('submitBtn');
  const brand = document.getElementById('brand').value.trim();
  const website = document.getElementById('website').value.trim() || null;
  const notes = document.getElementById('notes').value.trim() || null;

  if (!brand) {
    root.innerHTML = '<div class="warn-box">Please enter a brand/client name to research.</div>';
    return;
  }

  btn.disabled = true;
  root.innerHTML = `
    <div class="card loading-box">
      <div class="spinner"></div>
      <b>Researching ${esc(brand)} across public web, Wikipedia, and search indices...</b>
      <p style="font-size:13px;margin:6px 0 0;color:var(--text-muted);">Collecting sources, extracting claims, and grounding facts.</p>
    </div>`;

  try {
    const res = await fetch('/research/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ brand_name: brand, website: website, notes: notes, max_pages: 8 })
    });
    const analysis = await res.json();
    if (!res.ok) throw new Error(JSON.stringify(analysis));

    currentClientId = analysis.client.id;
    const profRes = await fetch(analysis.profile_url);
    const profile = await profRes.json();

    renderProfileView(profile, analysis);
  } catch (err) {
    root.innerHTML = `<div class="danger-box">Research failed: ${esc(err.message)}</div>`;
  } finally {
    btn.disabled = false;
  }
}

function renderProfileView(profile, analysis) {
  const root = document.getElementById('report');
  const getInf = cat => (profile.insights || []).filter(i => i.category === cat);
  const sw = (profile.insights || []).filter(i => ['strengths', 'weaknesses', 'opportunities'].includes(i.category));

  let html = `
    <div class="card" style="background:linear-gradient(135deg, rgba(15,98,254,0.15), rgba(168,85,247,0.15));border-color:var(--accent);">
      <h2 style="border:none;margin-bottom:8px;padding:0;">Client: ${esc(profile.client.name)}</h2>
      <div style="font-size:14px;color:#93c5fd;margin-bottom:12px;">
        ${profile.client.website ? `Official Website: <a href="${esc(profile.client.website)}" target="_blank" style="font-weight:600;color:var(--accent);">${esc(profile.client.website)}</a>` : 'Website: Not established'}
      </div>
      <div class="meta-badges">
        <span class="badge" style="background:var(--primary);color:white;">Status: ${esc(analysis.research_status)}</span>
        <span class="badge" style="background:rgba(56,189,248,0.2);color:#38bdf8;">Sources: ${analysis.sources_collected}</span>
        <span class="badge" style="background:var(--success-bg);color:#4ade80;">Facts: ${analysis.facts_extracted}</span>
        <span class="badge" style="background:var(--purple-bg);color:#c084fc;">Inferences: ${analysis.insights_generated}</span>
      </div>
      <p style="margin:12px 0 0;font-size:13.5px;color:#cbd5e1;">${esc(analysis.research_message)}</p>
    </div>`;

  html += renderSection('Summary', profile.summary);
  html += renderSection('Identity', profile.identity);
  html += renderSection('Business', profile.business);
  html += renderSection('Founder / Key People', profile.founder);
  html += renderSection('Niche & Category', profile.niche);
  html += renderSection('Products / Services / Offers', profile.offers);
  html += renderSection('Target Audience', profile.audience, getInf('audience'));
  html += renderSection('Brand & Positioning', profile.brand, getInf('brand'));
  html += renderSection('Social & Content Presence', profile.social_presence);
  html += renderSection('Competitors', profile.competitors, getInf('competitors'));
  html += renderSection('Marketing & Content Intelligence', profile.marketing_intelligence, getInf('marketing_intelligence'));

  if (sw.length) {
    html += `
      <section class="card">
        <h2><span>Strategic Inferences (SWOT)</span> <span class="count">${sw.length} insight(s)</span></h2>
        ${sw.map(renderInsight).join('')}
      </section>`;
  }

  if (profile.sources?.length) {
    html += `
      <section class="card">
        <h2><span>Sources Used</span> <span class="count">${profile.sources.length} sources</span></h2>
        <ul class="src-list">
          ${profile.sources.map(s => `
            <li class="src-item">
              <div>
                <a href="${esc(s.url || '#')}" target="_blank">${esc(s.title || s.url || s.id)}</a>
                <div style="font-size:11px;color:#64748b;margin-top:2px;">${esc(s.url || 'Local Reference')}</div>
              </div>
              <div class="meta-badges">
                <span class="badge badge-cat">${esc(s.metadata?.authority || s.source_type)}</span>
              </div>
            </li>
          `).join('')}
        </ul>
      </section>`;
  }

  root.innerHTML = html;
}

async function runVerification(checkLive) {
  if (!currentClientId) {
    const cRes = await fetch('/clients');
    const cl = await cRes.json();
    if (!cl.length) { alert('Please research a brand first.'); return; }
    currentClientId = cl[0].id;
  }

  const out = document.getElementById('verifier-output');
  out.innerHTML = `
    <div class="card loading-box">
      <div class="spinner"></div>
      <b>Running comprehensive fact-checking audit...</b>
      <p style="font-size:13px;margin:6px 0 0;color:var(--text-muted);">Auditing source reachability, grounding claims, and detecting contradictions.</p>
    </div>`;

  try {
    const res = await fetch(`/clients/${currentClientId}/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ check_live_urls: checkLive })
    });
    const report = await res.json();
    if (!res.ok) throw new Error(JSON.stringify(report));

    const scoreClass = report.overall_health_score >= 80 ? 'score-high' : (report.overall_health_score >= 50 ? 'score-med' : 'score-low');

    let html = `
      <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
          <div>
            <h2 style="border:none;margin:0;padding:0;">Evidence Health Audit: ${esc(report.client_name)}</h2>
            <div style="font-size:12px;color:var(--text-muted);margin-top:4px;">Audit Timestamp: ${esc(report.verified_at)}</div>
          </div>
          <div class="score-circle">
            <span class="score-val ${scoreClass}">${report.overall_health_score}/100</span>
          </div>
        </div>
        <div class="meta-badges">
          <span class="badge badge-strong">Grounded Facts: ${report.summary.grounded_facts}/${report.summary.total_facts}</span>
          <span class="badge badge-cat">Reachable Sources: ${report.summary.reachable_sources}/${report.summary.total_sources}</span>
          <span class="badge badge-inferred">Valid Inferences: ${report.summary.valid_insights}/${report.summary.total_insights}</span>
          <span class="badge ${report.summary.conflicts_count ? 'badge-weak' : 'badge-strong'}">Conflicts: ${report.summary.conflicts_count}</span>
        </div>
      </div>`;

    if (report.conflicts_detected?.length) {
      html += `
        <div class="danger-box">
          <b>⚠️ Contradictory Fact Conflicts Detected (${report.conflicts_detected.length}):</b>
          <ul style="margin:8px 0 0 18px;padding:0;font-size:13.5px;">
            ${report.conflicts_detected.map(c => `<li><b>${esc(c.category)}.${esc(c.key)}</b>: ${esc(c.message)}</li>`).join('')}
          </ul>
        </div>`;
    }

    if (report.recommendations?.length) {
      html += `
        <div class="card">
          <h2><span>Actionable Verification Recommendations</span></h2>
          <ul style="margin:0 0 0 18px;padding:0;font-size:14px;color:#cbd5e1;">
            ${report.recommendations.map(r => `<li style="margin-bottom:6px;">${esc(r)}</li>`).join('')}
          </ul>
        </div>`;
    }

    // Fact grounding breakdown
    html += `
      <div class="card">
        <h2><span>Fact Grounding Audit (All Active Claims)</span> <span class="count">${report.fact_results.length} claims</span></h2>`;
    for (const f of report.fact_results) {
      const gBadge = f.grounding_status === 'STRONG' ? 'badge-strong' : (f.grounding_status === 'MODERATE' ? 'badge-moderate' : 'badge-weak');
      html += `
        <div class="fact-item">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <div class="fact-key">${esc(f.category)}.${esc(f.key)}</div>
            <span class="badge ${gBadge}">${esc(f.grounding_status)} (${Math.round(f.grounding_score*100)}%)</span>
          </div>
          <div class="fact-val">${formatValue(f.value)}</div>
          <div class="meta-badges">
            <span class="badge badge-conf">Calibrated Conf: ${Math.round(f.calibrated_confidence*100)}%</span>
            <span class="badge badge-cat">${f.verified_sources_count} verified source(s)</span>
          </div>
          ${f.matching_snippets?.length ? `<div style="font-size:12px;color:#94a3b8;margin-top:6px;font-style:italic;">Evidence: ${esc(f.matching_snippets[0])}</div>` : ''}
        </div>`;
    }
    html += `</div>`;

    out.innerHTML = html;
  } catch (err) {
    out.innerHTML = `<div class="danger-box">Verification failed: ${esc(err.message)}</div>`;
  }
}

async function loadYTJson() {
  const out = document.getElementById('yt-output');
  if (!currentClientId) {
    const cRes = await fetch('/clients');
    const cl = await cRes.json();
    if (!cl.length) { alert('Please research a brand first.'); return; }
    currentClientId = cl[0].id;
  }

  try {
    const res = await fetch(`/clients/${currentClientId}/export/yt-searcher`);
    currentClientJson = await res.json();
    out.innerHTML = `
      <div class="card">
        <h2><span>Generated client.json Contract</span> <span class="count">${Object.keys(currentClientJson).length} fields</span></h2>
        <pre>${esc(JSON.stringify(currentClientJson, null, 2))}</pre>
      </div>`;
  } catch (err) {
    out.innerHTML = `<div class="danger-box">Error loading YT-Searcher contract: ${esc(err.message)}</div>`;
  }
}

async function syncToYTSearcher() {
  if (!currentClientId) { alert('Please research a brand first.'); return; }
  try {
    const res = await fetch(`/clients/${currentClientId}/export/yt-searcher/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ output_path: "/home/xor_sensei/Dev/Viralyst/RAG/client.json" })
    });
    const data = await res.json();
    alert(`✓ Successfully synced client.json to:\n${data.path}\n\nYT-Searcher is ready to run retrieval with:\npython -m youtube_searcher plan --client client.json`);
  } catch (err) {
    alert('Sync failed: ' + err.message);
  }
}

function copyClientJson() {
  if (!currentClientJson) return;
  navigator.clipboard.writeText(JSON.stringify(currentClientJson, null, 2));
  alert('Copied client.json to clipboard!');
}

function downloadClientJson() {
  if (!currentClientJson) return;
  const blob = new Blob([JSON.stringify(currentClientJson, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `client_${currentClientJson.business_name || 'profile'}.json`;
  a.click();
}

async function runAsk() {
  if (!currentClientId) {
    const cRes = await fetch('/clients');
    const cl = await cRes.json();
    if (!cl.length) { alert('Please research a brand first.'); return; }
    currentClientId = cl[0].id;
  }

  const q = document.getElementById('askInput').value.trim();
  if (!q) return;

  const out = document.getElementById('ask-output');
  out.innerHTML = `<div class="card loading-box"><div class="spinner"></div><b>Retrieving evidence...</b></div>`;

  try {
    const res = await fetch(`/clients/${currentClientId}/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: q })
    });
    const ans = await res.json();
    let html = `
      <div class="card">
        <h2><span>Answer</span></h2>
        <p style="font-size:15px;color:#f8fafc;margin:0 0 14px;">${esc(ans.answer)}</p>`;

    if (ans.known_facts?.length) {
      html += `<h3>Known Verified Facts (${ans.known_facts.length})</h3>${ans.known_facts.map(renderFact).join('')}`;
    }
    if (ans.inferences?.length) {
      html += `<h3>Strategic Inferences (${ans.inferences.length})</h3>${ans.inferences.map(renderInsight).join('')}`;
    }
    if (ans.unknown?.length) {
      html += `<div class="warn-box" style="margin-top:14px;"><b>Explicit Unknowns:</b> ${ans.unknown.map(esc).join(', ')}</div>`;
    }
    html += `</div>`;
    out.innerHTML = html;
  } catch (err) {
    out.innerHTML = `<div class="danger-box">Ask failed: ${esc(err.message)}</div>`;
  }
}
</script>
</body>
</html>"""

