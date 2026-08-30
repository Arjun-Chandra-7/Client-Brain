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
        "verification_report": result.get("verification_report", {}),
        "evidence_health_score": result.get("evidence_health_score", 100.0),
        "yt_client_json": result.get("yt_client_json", {}),
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
<title>VIRALYST Client Brain — Intelligence Dashboard & YT-Searcher Report</title>
<style>
:root {
  --primary: #3b82f6;
  --primary-hover: #2563eb;
  --bg: #0b0f19;
  --surface: #111827;
  --surface-alt: #1f2937;
  --text: #f9fafb;
  --text-muted: #9ca3af;
  --border: #374151;
  --card-border: #4b5563;
  --accent: #38bdf8;
  --success: #10b981;
  --success-bg: rgba(16, 185, 129, 0.12);
  --warning: #f59e0b;
  --warning-bg: rgba(245, 158, 11, 0.12);
  --danger: #ef4444;
  --danger-bg: rgba(239, 68, 68, 0.12);
  --purple: #a855f7;
  --purple-bg: rgba(168, 85, 247, 0.12);
}
* { box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  max-width: 1240px;
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
  flex-wrap: wrap;
  gap: 12px;
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
  width: 42px;
  height: 42px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 15px rgba(59, 130, 246, 0.4);
}
h1 {
  font-size: 23px;
  font-weight: 700;
  margin: 0;
  letter-spacing: -0.4px;
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
  padding: 7px 13px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  text-decoration: none;
  transition: all 0.15s ease;
}
.nav-btn:hover {
  background: var(--primary);
  color: #fff;
  border-color: var(--primary);
}
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 22px;
  margin-bottom: 20px;
  box-shadow: 0 4px 14px rgba(0,0,0,0.25);
}
.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.grid-3 {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 16px;
}
@media (max-width: 840px) {
  .grid-2, .grid-3 { grid-template-columns: 1fr; }
}
.form-group {
  margin-bottom: 14px;
}
label {
  display: block;
  font-weight: 600;
  font-size: 12.5px;
  margin-bottom: 5px;
  color: #e5e7eb;
}
input, textarea {
  width: 100%;
  padding: 10px 13px;
  background: #030712;
  border: 1px solid #374151;
  border-radius: 8px;
  font-size: 13.5px;
  color: #f9fafb;
  outline: none;
  transition: border-color 0.15s ease;
  font-family: inherit;
}
input:focus, textarea:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2);
}
.btn {
  background: var(--primary);
  color: #ffffff;
  border: 0;
  border-radius: 8px;
  padding: 11px 22px;
  font-size: 14.5px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.btn:hover { background: var(--primary-hover); transform: translateY(-1px); }
.btn-secondary { background: var(--surface-alt); color: #e5e7eb; }
.btn-secondary:hover { background: #374151; }
.btn-success { background: #059669; }
.btn-success:hover { background: #047857; }
.btn-warning { background: #d97706; }
.btn-warning:hover { background: #b45309; }
.btn:disabled { background: #374151; color: #6b7280; cursor: not-allowed; transform: none; }

.pill {
  display: inline-block;
  padding: 4px 10px;
  background: rgba(56, 189, 248, 0.12);
  color: #38bdf8;
  border: 1px solid rgba(56, 189, 248, 0.3);
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
  margin: 3px 4px 3px 0;
}
.pill-danger {
  background: rgba(239, 68, 68, 0.12);
  color: #f87171;
  border-color: rgba(239, 68, 68, 0.3);
}
.pill-purple {
  background: rgba(168, 85, 247, 0.12);
  color: #c084fc;
  border-color: rgba(168, 85, 247, 0.3);
}
.pill-success {
  background: rgba(16, 185, 129, 0.12);
  color: #34d399;
  border-color: rgba(16, 185, 129, 0.3);
}
.pill-warning {
  background: rgba(245, 158, 11, 0.12);
  color: #fbbf24;
  border-color: rgba(245, 158, 11, 0.3);
}

.report-section {
  background: #111827;
  border: 1px solid #1f2937;
  border-radius: 10px;
  padding: 16px 18px;
  margin-bottom: 14px;
}
.report-title {
  font-size: 13px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--accent);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.report-list {
  margin: 0;
  padding-left: 18px;
  font-size: 14px;
  color: #e5e7eb;
}
.report-list li {
  margin-bottom: 5px;
}

.score-circle {
  font-size: 26px;
  font-weight: 800;
  display: flex;
  align-items: center;
  gap: 8px;
}
.score-val {
  padding: 3px 12px;
  border-radius: 8px;
}
.score-high { background: var(--success-bg); color: #34d399; border: 1px solid #10b981; }
.score-med { background: var(--warning-bg); color: #fbbf24; border: 1px solid #f59e0b; }
.score-low { background: var(--danger-bg); color: #f87171; border: 1px solid #ef4444; }

.badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
  text-transform: uppercase;
  font-size: 10.5px;
  letter-spacing: 0.3px;
  display: inline-block;
}
.badge-researched { background: var(--success-bg); color: #34d399; }
.badge-inferred { background: var(--purple-bg); color: #c084fc; }
.badge-conf { background: rgba(255,255,255,0.08); color: #d1d5db; }
.badge-cat { background: rgba(56, 189, 248, 0.12); color: #38bdf8; }

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

pre {
  background: #030712;
  color: #e5e7eb;
  padding: 14px;
  border-radius: 8px;
  overflow-x: auto;
  font-size: 12.5px;
  border: 1px solid #1f2937;
  max-height: 440px;
}
details {
  background: #111827;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 16px;
  margin-top: 14px;
}
details summary {
  cursor: pointer;
  font-weight: 600;
  font-size: 13.5px;
  color: #f3f4f6;
}
</style>
</head>
<body>

<header>
  <div class="brand-title">
    <div class="brand-logo">CB</div>
    <div>
      <h1>VIRALYST Client Brain</h1>
      <p class="subtitle">Client Intelligence Ingestion, Fact Checking & YT-Searcher Report Builder</p>
    </div>
  </div>
  <div class="nav-links">
    <a href="/docs" target="_blank" class="nav-btn">API Documentation</a>
    <a href="https://github.com/Arjun-Chandra-7/Client-Brain" target="_blank" class="nav-btn">GitHub Repository</a>
  </div>
</header>

<!-- CLIENT INPUT & WEB CRAWL FORM -->
<div class="card">
  <h2 style="font-size:16px;margin:0 0 14px;color:#f9fafb;display:flex;align-items:center;gap:8px;">
    <span>⚡ Client Intelligence Discovery & YT-Searcher Report</span>
  </h2>
  
  <div class="grid-2">
    <div class="form-group">
      <label for="brand">Client / Brand Name * (Only required field)</label>
      <input id="brand" placeholder="e.g. Alex Hormozi, Gymshark, Basecamp, Nike, Notion, Duolingo, Hubspot..." autofocus>
    </div>
    <div class="form-group">
      <label for="website">Official Website URL (Optional — will auto-discover if blank)</label>
      <input id="website" placeholder="e.g. https://example.com">
    </div>
  </div>

  <div class="form-group">
    <label for="notes">Client Notes, Context or Background (Optional — paste anything you want to provide)</label>
    <textarea id="notes" rows="2" placeholder="Any private briefing notes, specific offer angles, target audience focus, constraints, or links... (leave blank to let internet discovery do the work)"></textarea>
  </div>

  <details style="margin-bottom:16px;background:#030712;border:1px solid #1f2937;">
    <summary style="font-size:13px;color:#9ca3af;">+ Add Optional Details (Niche, Competitors, Goals, Exclusions)</summary>
    <div style="margin-top:12px;">
      <div class="grid-2">
        <div class="form-group">
          <label for="niche">Target Niche / Vertical (Optional)</label>
          <input id="niche" placeholder="e.g. Fitness Coaching, B2B SaaS, Real Estate...">
        </div>
        <div class="form-group">
          <label for="competitors">Known Competitors (Optional, comma-separated)</label>
          <input id="competitors" placeholder="e.g. Competitor A, Competitor B...">
        </div>
      </div>
      <div class="grid-2">
        <div class="form-group">
          <label for="goals">Goals & Desired Outcomes (Optional, comma-separated)</label>
          <input id="goals" placeholder="e.g. Acquire agency leads, Drive YouTube Shorts reach...">
        </div>
        <div class="form-group">
          <label for="constraints">Negative Exclusions & Safety Limits (Optional, comma-separated)</label>
          <input id="constraints" placeholder="e.g. No get-rich-quick, No supplement reviews...">
        </div>
      </div>
    </div>
  </details>

  <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;">
    <button id="submitBtn" class="btn" onclick="generateReport()">
      ⚡ Pull Internet Intelligence & Curate YT-Searcher Report
    </button>
    <button class="btn btn-secondary" onclick="loadLatestSavedProfile()">
      Load Current Active Client
    </button>
  </div>
</div>

<!-- RESULTS CONTAINER -->
<div id="output"></div>

<script>
let currentClientId = null;
let currentClientJson = null;

const esc = s => String(s ?? '').replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));

function parseCsv(str) {
  if (!str) return [];
  return str.split(',').map(s => s.trim()).filter(Boolean);
}

async function generateReport() {
  const root = document.getElementById('output');
  const btn = document.getElementById('submitBtn');

  const brand = document.getElementById('brand').value.trim();
  const website = document.getElementById('website').value.trim() || null;
  const niche = document.getElementById('niche').value.trim() || null;
  const competitors = parseCsv(document.getElementById('competitors').value);
  const goals = parseCsv(document.getElementById('goals').value);
  const constraints = parseCsv(document.getElementById('constraints').value);
  const notes = document.getElementById('notes').value.trim() || null;

  if (!brand) {
    alert('Please provide a Client / Brand Name.');
    return;
  }

  btn.disabled = true;
  root.innerHTML = `
    <div class="card loading-box">
      <div class="spinner"></div>
      <b style="font-size:16px;color:#f9fafb;">Pulling Web Intelligence & Building YT-Searcher Report for "${esc(brand)}"...</b>
      <p style="font-size:13px;margin:8px 0 0;color:var(--text-muted);">
        1. Ingesting client parameters • 2. Crawling official pages & Wikipedia • 3. Extracting evidence facts • 4. Auditing grounding • 5. Building YT-Searcher profile
      </p>
    </div>`;

  try {
    const res = await fetch('/research/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        brand_name: brand,
        website: website,
        niche: niche,
        notes: notes,
        competitors: competitors,
        goals: goals,
        constraints: constraints,
        max_pages: 8
      })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(JSON.stringify(data));

    currentClientId = data.client.id;
    currentClientJson = data.yt_client_json;

    // Fetch full profile for detailed evidence breakdown
    const profRes = await fetch(data.profile_url);
    const profile = await profRes.json();

    renderDashboard(data, profile);
  } catch (err) {
    root.innerHTML = `
      <div class="card" style="background:var(--danger-bg);border-color:var(--danger);color:#fecaca;">
        <b>Error generating report:</b> ${esc(err.message)}
      </div>`;
  } finally {
    btn.disabled = false;
  }
}

async function loadLatestSavedProfile() {
  try {
    const res = await fetch('/clients');
    const clients = await res.json();
    if (!clients.length) {
      alert('No clients found in database.');
      return;
    }
    const latest = clients[0];
    currentClientId = latest.id;

    const [profRes, ytRes] = await Promise.all([
      fetch(`/clients/${latest.id}/profile`),
      fetch(`/clients/${latest.id}/export/yt-searcher`)
    ]);

    const profile = await profRes.json();
    const ytJson = await ytRes.json();
    currentClientJson = ytJson;

    renderDashboard({
      client: profile.client,
      sources_collected: profile.sources?.length || 0,
      facts_extracted: profile.facts?.length || 0,
      insights_generated: profile.insights?.length || 0,
      evidence_health_score: profile.evidence_health_score || 100,
      verification_report: profile.verification_report || {},
      yt_client_json: ytJson,
      research_message: "Loaded client profile directly from local evidence database."
    }, profile);
  } catch (err) {
    alert('Error loading profile: ' + err.message);
  }
}

function renderPills(items, type = 'normal') {
  if (!items || !items.length) return '<span style="color:var(--text-muted);font-size:13px;">None specified</span>';
  const colorCls = type === 'danger' ? 'pill-danger' : (type === 'purple' ? 'pill-purple' : (type === 'success' ? 'pill-success' : (type === 'warning' ? 'pill-warning' : '')));
  return items.map(item => `<span class="pill ${colorCls}">${esc(item)}</span>`).join('');
}

function renderDashboard(data, profile) {
  const root = document.getElementById('output');
  const yt = data.yt_client_json || {};
  const comp = yt.company_overview || {};
  const vRep = data.verification_report || {};
  const healthScore = data.evidence_health_score || 100;
  const scoreClass = healthScore >= 80 ? 'score-high' : (healthScore >= 50 ? 'score-med' : 'score-low');

  let html = `
    <!-- TOP OVERVIEW HEADER -->
    <div class="card" style="background:linear-gradient(135deg, rgba(59,130,246,0.12), rgba(168,85,247,0.12));border-color:var(--accent);">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:14px;">
        <div>
          <div style="display:flex;align-items:center;gap:8px;">
            <span class="badge" style="background:var(--primary);color:#fff;">VIRALYST READY</span>
            <span class="badge badge-cat">${esc(yt.industry || 'Business')}</span>
          </div>
          <h2 style="font-size:22px;margin:6px 0 4px;color:#fff;">${esc(yt.company_name || yt.business_name || profile.client.name)}</h2>
          <div style="font-size:13.5px;color:#93c5fd;">
            ${yt.website ? `Official Website: <a href="${esc(yt.website)}" target="_blank" style="color:var(--accent);font-weight:600;">${esc(yt.website)}</a>` : 'Website: None'}
          </div>
        </div>

        <div style="text-align:right;">
          <div style="font-size:11px;font-weight:700;text-transform:uppercase;color:var(--text-muted);letter-spacing:0.5px;">Evidence Health Score</div>
          <div class="score-circle" style="justify-content:flex-end;margin-top:2px;">
            <span class="score-val ${scoreClass}">${healthScore}/100</span>
          </div>
        </div>
      </div>

      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:12px;">
        <span class="badge badge-cat">Sources Harvested: ${data.sources_collected}</span>
        <span class="badge badge-researched">Grounded Claims: ${vRep.summary?.grounded_facts || data.facts_extracted}/${data.facts_extracted}</span>
        <span class="badge badge-inferred">Inferences: ${data.insights_generated}</span>
        <span class="badge ${vRep.summary?.conflicts_count ? 'badge-weak' : 'badge-researched'}">Conflicts: ${vRep.summary?.conflicts_count || 0}</span>
      </div>

      <div style="margin-top:12px;padding:8px 12px;background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.3);border-radius:6px;font-size:13px;color:#a7f3d0;display:flex;align-items:center;gap:8px;">
        <span>📁 <b>Auto-Saved to Folder:</b> <code style="color:#34d399;font-weight:700;">Client info/client.json</code> &amp; <code style="color:#34d399;font-weight:700;">Client info/${esc((yt.company_name || yt.business_name || 'client').replace(/[^a-zA-Z0-9_ -]/g, '').trim().replace(/ /g, '_'))}.json</code></span>
      </div>

      <div style="display:flex;gap:10px;margin-top:16px;flex-wrap:wrap;">
        <button class="btn btn-success" onclick="copyClientJson()">📋 Copy client.json</button>
        <button class="btn btn-secondary" onclick="downloadClientJson()">⬇️ Download client.json</button>
      </div>
    </div>`;

  if (vRep.conflicts_detected?.length) {
    html += `
      <div class="card" style="background:var(--danger-bg);border-color:var(--danger);color:#fecaca;">
        <b>⚠️ Integrated Fact-Check Notice: Contradictory Claims Detected (${vRep.conflicts_detected.length})</b>
        <ul style="margin:6px 0 0 18px;font-size:13px;">
          ${vRep.conflicts_detected.map(c => `<li><b>${esc(c.category)}.${esc(c.key)}</b>: ${esc(c.message)}</li>`).join('')}
        </ul>
      </div>`;
  }

  // 1. COMPANY & BUSINESS DETAILS CARD
  html += `
    <div class="card">
      <h3 style="margin:0 0 16px;font-size:17px;color:#fff;border-bottom:1px solid var(--border);padding-bottom:8px;display:flex;align-items:center;gap:8px;">
        <span>🏢 Company Background & Leadership Details</span>
      </h3>

      <div class="grid-2">
        <div class="report-section">
          <div class="report-title">🏛️ Entity & Industry</div>
          <div style="font-size:14px;color:#e5e7eb;line-height:1.6;">
            <div><b>Legal Name:</b> ${esc(comp.legal_name || yt.business_name)}</div>
            <div><b>Industry / Vertical:</b> ${esc(yt.industry || 'Technology & Commerce')}</div>
            ${comp.headquarters ? `<div><b>Headquarters:</b> ${esc(comp.headquarters)}</div>` : ''}
            ${comp.founding_details ? `<div><b>Founded:</b> ${esc(comp.founding_details)}</div>` : ''}
          </div>
        </div>

        <div class="report-section">
          <div class="report-title">👥 Founders & Key Leadership</div>
          <div style="font-size:14px;color:#e5e7eb;line-height:1.6;">
            <div><b>Founders:</b> ${esc(comp.founders || 'Documented in public registry')}</div>
            ${comp.leadership ? `<div><b>Leadership / CEO:</b> ${esc(comp.leadership)}</div>` : ''}
            ${comp.revenue_scale ? `<div><b>Scale / Revenue:</b> ${esc(comp.revenue_scale)}</div>` : ''}
            <div><b>Business Model:</b> ${esc(comp.business_model || 'Subscription & commercial operations')}</div>
          </div>
        </div>
      </div>

      ${comp.executive_summary ? `
        <div class="report-section" style="margin-bottom:0;">
          <div class="report-title">📄 Executive Summary & Mission</div>
          <div style="font-size:13.5px;color:#d1d5db;line-height:1.5;">${esc(comp.executive_summary)}</div>
        </div>
      ` : ''}
    </div>`;

  // 2. STRUCTURED YT-SEARCHER RETRIEVAL PROFILE CARD
  html += `
    <div class="card">
      <h3 style="margin:0 0 16px;font-size:17px;color:#fff;border-bottom:1px solid var(--border);padding-bottom:8px;display:flex;align-items:center;gap:8px;">
        <span>📦 YT-Searcher Retrieval Profile (Strict YT-Searcher Contract)</span>
      </h3>

      <div class="grid-2">
        <div class="report-section">
          <div class="report-title">🏷️ Niches & Subniches</div>
          <div style="margin-bottom:8px;">${renderPills(yt.subniches)}</div>
          <div style="font-size:12px;color:var(--text-muted);">Primary: <b style="color:#93c5fd;">${esc(yt.primary_niche)}</b></div>
        </div>

        <div class="report-section">
          <div class="report-title">🎯 Target Audience & Buyer Personas</div>
          <div>${renderPills(yt.target_audience, 'purple')}</div>
        </div>
      </div>

      <div class="grid-2">
        <div class="report-section">
          <div class="report-title">💥 Customer Problems & Pain Points</div>
          <div>${renderPills(yt.pain_points, 'danger')}</div>
        </div>

        <div class="report-section">
          <div class="report-title">📦 Flagship Offers, Products & Services</div>
          <div>${renderPills(yt.products, 'success')}</div>
        </div>
      </div>

      <div class="grid-2">
        <div class="report-section">
          <div class="report-title">🏛️ Content Pillars (Formats & Themes)</div>
          <div>${renderPills(yt.content_pillars)}</div>
        </div>

        <div class="report-section">
          <div class="report-title">💡 Authoritative Topics & Concepts</div>
          <div>${renderPills(yt.topics, 'purple')}</div>
        </div>
      </div>

      <div class="grid-2">
        <div class="report-section">
          <div class="report-title">🔑 Target Search Queries & Video Hooks</div>
          <div>${renderPills(yt.keywords, 'warning')}</div>
        </div>

        <div class="report-section">
          <div class="report-title">⚔️ Competitor & Creator Channel Seeds</div>
          <div>${renderPills(yt.competitors?.concat(yt.creators || []))}</div>
        </div>
      </div>

      <div class="report-section">
        <div class="report-title">🚫 Negative Exclusions (Safety Guardrails)</div>
        <div>${renderPills(yt.exclusions, 'danger')}</div>
      </div>

      ${yt.brand_positioning ? `
        <div class="report-section" style="margin-bottom:0;">
          <div class="report-title">✨ Brand Positioning & Tone</div>
          <div style="font-size:13.5px;color:#e5e7eb;margin-bottom:6px;"><b>Positioning:</b> ${esc(yt.brand_positioning)}</div>
          <div style="font-size:13.5px;color:#e5e7eb;"><b>Tone of Voice:</b> ${esc(yt.tone_of_voice || 'Direct, authoritative & clear')}</div>
        </div>
      ` : ''}
    </div>`;

  // RAW JSON ACCORDION
  html += `
    <details>
      <summary>👁️ View Raw client.json (Ready for YT-Searcher)</summary>
      <div style="margin-top:10px;">
        <button class="btn btn-secondary" style="margin-bottom:10px;padding:6px 12px;font-size:12px;" onclick="copyClientJson()">📋 Copy Raw JSON</button>
        <pre>${esc(JSON.stringify(yt, null, 2))}</pre>
      </div>
    </details>`;

  // EVIDENCE FACTS ACCORDION
  if (profile.facts?.length) {
    html += `
      <details>
        <summary>🛡️ View Full Evidence Ledger (${profile.facts.length} Verified Facts & Sources)</summary>
        <div style="margin-top:12px;">
          ${profile.facts.map(f => `
            <div style="padding:10px 0;border-bottom:1px solid #1f2937;">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="font-size:11.5px;font-weight:700;color:var(--accent);text-transform:uppercase;">${esc(f.category)}.${esc(f.key)}</span>
                <span class="badge badge-conf">Conf: ${Math.round((f.confidence||0)*100)}%</span>
              </div>
              <div style="font-size:13.5px;color:#f3f4f6;margin:4px 0;">${typeof f.value === 'object' ? JSON.stringify(f.value) : esc(f.value)}</div>
              <div style="font-size:11px;color:#6b7280;">Provenance: ${f.source_ids?.length || 0} linked source(s) • Type: ${esc(f.fact_type)}</div>
            </div>
          `).join('')}
        </div>
      </details>`;
  }

  root.innerHTML = html;
}

function copyClientJson() {
  if (!currentClientJson) return;
  navigator.clipboard.writeText(JSON.stringify(currentClientJson, null, 2));
  alert('✓ client.json successfully copied to clipboard!');
}

function downloadClientJson() {
  if (!currentClientJson) return;
  const name = (currentClientJson.business_name || 'client').toLowerCase().replace(/[^a-z0-9]/g, '_');
  const blob = new Blob([JSON.stringify(currentClientJson, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `client_${name}.json`;
  a.click();
}
</script>
</body>
</html>"""


