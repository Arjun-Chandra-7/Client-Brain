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
<title>Client Brain | Systematic Brand Research & Intelligence</title>
<style>
:root {
  --primary: #0f62fe;
  --primary-hover: #0353e9;
  --bg: #f4f6f8;
  --surface: #ffffff;
  --text: #161616;
  --text-muted: #525252;
  --border: #e0e0e0;
  --card-border: #d0d7de;
  --tag-bg: #edf5ff;
  --tag-text: #0043ce;
  --badge-res: #defbe6;
  --badge-res-text: #0e6027;
  --badge-inf: #f6f2ff;
  --badge-inf-text: #6929c4;
  --warn-bg: #fff8e1;
  --warn-border: #ffe082;
  --warn-text: #8d6e63;
}
* { box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  max-width: 1100px;
  margin: 0 auto;
  padding: 32px 20px 80px;
  color: var(--text);
  background: var(--bg);
  line-height: 1.5;
}
header {
  margin-bottom: 24px;
}
h1 {
  font-size: 28px;
  font-weight: 700;
  margin: 0 0 6px;
  letter-spacing: -0.5px;
}
p.subtitle {
  color: var(--text-muted);
  margin: 0;
  font-size: 15px;
}
.card {
  background: var(--surface);
  border: 1px solid var(--card-border);
  border-radius: 10px;
  padding: 22px;
  margin-bottom: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.form-group {
  margin-bottom: 14px;
}
label {
  display: block;
  font-weight: 600;
  font-size: 13px;
  margin-bottom: 5px;
  color: #393939;
}
input, textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #c6c6c6;
  border-radius: 6px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.15s ease;
  font-family: inherit;
}
input:focus, textarea:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 2px rgba(15,98,254,0.15);
}
button {
  background: var(--primary);
  color: #ffffff;
  border: 0;
  border-radius: 6px;
  padding: 11px 22px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s ease;
}
button:hover {
  background: var(--primary-hover);
}
button:disabled {
  background: #a8a8a8;
  cursor: not-allowed;
}
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
@media (max-width: 768px) {
  .grid { grid-template-columns: 1fr; }
}
.fact-item {
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
}
.fact-item:last-child {
  border-bottom: none;
}
.fact-key {
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
  margin-bottom: 4px;
}
.fact-val {
  font-size: 14.5px;
  color: var(--text);
  margin-bottom: 6px;
  word-break: break-word;
}
.fact-val ul {
  margin: 4px 0 0 18px;
  padding: 0;
}
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
.badge-researched { background: var(--badge-res); color: var(--badge-res-text); }
.badge-inferred { background: var(--badge-inf); color: var(--badge-inf-text); }
.badge-conf { background: #e8e8e8; color: #393939; }
.badge-cat { background: var(--tag-bg); color: var(--tag-text); }
.warn-box {
  background: var(--warn-bg);
  border: 1px solid var(--warn-border);
  color: var(--warn-text);
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
  border: 3px solid #e0e0e0;
  border-top: 3px solid var(--primary);
  border-radius: 50%;
  width: 28px;
  height: 28px;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 12px;
}
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
h2 {
  font-size: 18px;
  font-weight: 700;
  margin: 0 0 14px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f0f0f0;
  color: #111;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
h2 .count {
  font-size: 12px;
  font-weight: normal;
  color: var(--text-muted);
}
.insight-card {
  background: #fcfaff;
  border: 1px solid #e8daff;
  border-radius: 6px;
  padding: 12px 14px;
  margin-bottom: 10px;
}
.insight-statement {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 6px;
  color: #2b1c40;
}
.src-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.src-item {
  padding: 8px 0;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13.5px;
}
.src-item:last-child { border-bottom: none; }
.src-item a { color: var(--primary); text-decoration: none; font-weight: 500; }
.src-item a:hover { text-decoration: underline; }
details {
  margin-top: 20px;
  background: #f4f4f4;
  border-radius: 6px;
  padding: 10px 14px;
}
details summary {
  cursor: pointer;
  font-weight: 600;
  font-size: 13px;
  color: #333;
}
pre {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 12px;
  margin-top: 10px;
}
</style>
</head>
<body>

<header>
  <h1>Client Brain</h1>
  <p class="subtitle">Systematic public brand research, source-backed evidence ledger, and separate strategic inferences.</p>
</header>

<div class="card">
  <div class="grid">
    <div class="form-group">
      <label for="brand">Brand / Client Name *</label>
      <input id="brand" placeholder="e.g. Starbucks, Basecamp, Gymshark">
    </div>
    <div class="form-group">
      <label for="website">Official Website (optional / recommended)</label>
      <input id="website" placeholder="https://www.example.com">
    </div>
  </div>
  <div class="form-group">
    <label for="notes">Private Notes or Context (optional)</label>
    <textarea id="notes" rows="2" placeholder="Any internal background, target objectives, or constraints..."></textarea>
  </div>
  <button id="submitBtn" onclick="runResearch()">Research Brand</button>
</div>

<div id="report"></div>

<script>
const esc = s => String(s ?? '').replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));

function formatValue(v) {
  if (Array.isArray(v)) {
    return `<ul>${v.map(item => `<li>${esc(item)}</li>`).join('')}</ul>`;
  }
  if (typeof v === 'object' && v !== null) {
    return `<pre style="margin:4px 0;background:#f9f9f9;color:#222;padding:8px;">${esc(JSON.stringify(v, null, 2))}</pre>`;
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
        ${f.source_ids?.length ? `<span class="badge" style="background:#eef;color:#338">${f.source_ids.length} source(s)</span>` : ''}
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
        <span class="badge" style="background:#eef;color:#338">${(i.supporting_fact_ids||[]).length} supporting fact(s)</span>
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
      <b>Researching ${esc(brand)} across public web, knowledge bases, and encyclopedic references...</b>
      <p style="font-size:13px;margin:6px 0 0;">Collecting multiple sources, extracting published claims, and separating source-backed facts from strategic inferences.</p>
    </div>`;

  try {
    const res = await fetch('/research/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ brand_name: brand, website: website, notes: notes, max_pages: 8 })
    });
    const analysis = await res.json();
    if (!res.ok) throw new Error(JSON.stringify(analysis));

    const profRes = await fetch(analysis.profile_url);
    const profile = await profRes.json();

    const getInf = cat => (profile.insights || []).filter(i => i.category === cat);
    const sw = (profile.insights || []).filter(i => ['strengths', 'weaknesses', 'opportunities'].includes(i.category));

    let html = `
      <div class="card" style="background:#f0f7ff;border-color:#b9daff;">
        <h2 style="border:none;margin-bottom:8px;padding:0;">Client Overview: ${esc(profile.client.name)}</h2>
        <div style="font-size:14px;color:#1e3a8a;margin-bottom:12px;">
          ${profile.client.website ? `Official Website: <a href="${esc(profile.client.website)}" target="_blank" style="font-weight:600;color:var(--primary);">${esc(profile.client.website)}</a>` : 'Website: Not established'}
        </div>
        <div class="meta-badges">
          <span class="badge" style="background:#155eef;color:white;">Status: ${esc(analysis.research_status)}</span>
          <span class="badge" style="background:#e0f2fe;color:#0369a1;">Sources: ${analysis.sources_collected}</span>
          <span class="badge" style="background:#dcfce7;color:#15803d;">Facts Extracted: ${analysis.facts_extracted}</span>
          <span class="badge" style="background:#f3e8ff;color:#7e22ce;">Inferences: ${analysis.insights_generated}</span>
        </div>
        <p style="margin:12px 0 0;font-size:13.5px;color:#334155;">${esc(analysis.research_message)}</p>
      </div>`;

    // Render structured report cards
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

    // Strengths / Weaknesses / Opportunities
    if (sw.length) {
      html += `
        <section class="card">
          <h2><span>Strengths / Weaknesses / Opportunities</span> <span class="count">${sw.length} insight(s)</span></h2>
          ${sw.map(renderInsight).join('')}
        </section>`;
    }

    // All Key Insights
    if (profile.insights?.length) {
      html += `
        <section class="card">
          <h2><span>All Strategic Insights & Inferences</span> <span class="count">${profile.insights.length} total</span></h2>
          ${profile.insights.map(renderInsight).join('')}
        </section>`;
    }

    // Missing Information
    if (profile.missing_information?.length) {
      html += `
        <section class="card">
          <h2>Missing Information</h2>
          <p style="font-size:13px;color:var(--text-muted);margin:0 0 10px;">Genuinely important information that could not be established from public evidence alone:</p>
          <ul style="margin:0 0 0 20px;padding:0;font-size:14px;color:#444;">
            ${profile.missing_information.map(m => `<li>${esc(m)}</li>`).join('')}
          </ul>
        </section>`;
    }

    // Sources Used
    if (profile.sources?.length) {
      html += `
        <section class="card">
          <h2><span>Sources Used</span> <span class="count">${profile.sources.length} sources</span></h2>
          <ul class="src-list">
            ${profile.sources.map(s => `
              <li class="src-item">
                <div>
                  <a href="${esc(s.url || '#')}" target="_blank">${esc(s.title || s.url || s.id)}</a>
                  <div style="font-size:11px;color:#666;margin-top:2px;">${esc(s.url || 'No URL')}</div>
                </div>
                <div class="meta-badges">
                  <span class="badge badge-cat">${esc(s.metadata?.authority || s.source_type)}</span>
                </div>
              </li>
            `).join('')}
          </ul>
        </section>`;
    }

    // Raw JSON details
    html += `
      <details>
        <summary>View Raw JSON Data</summary>
        <pre>${esc(JSON.stringify({ analysis, profile }, null, 2))}</pre>
      </details>`;

    root.innerHTML = html;
  } catch (err) {
    root.innerHTML = `<div class="warn-box">Research failed: ${esc(err.message)}</div>`;
  } finally {
    btn.disabled = false;
  }
}
</script>
</body>
</html>"""
