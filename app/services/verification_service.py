from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import re
from typing import Any
import urllib.request
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Client, Fact, FactType, Insight, RecordStatus, Source
from app.services.fact_service import FactService


@dataclass
class SourceHealth:
    source_id: str
    url: str | None
    source_type: str
    status: str  # "reachable", "unreachable", "local_only", "redirected"
    http_code: int | None = None
    response_time_ms: float | None = None
    content_length: int | None = None
    error_message: str | None = None
    last_checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class FactVerificationResult:
    fact_id: str
    category: str
    key: str
    value: Any
    fact_type: str
    original_confidence: float
    calibrated_confidence: float
    grounding_status: str  # "STRONG", "MODERATE", "WEAK", "UNGROUNDED", "UNVERIFIED"
    grounding_score: float  # 0.0 - 1.0
    verified_sources_count: int
    matching_snippets: list[str]
    conflicts: list[str]
    notes: list[str]


@dataclass
class InsightVerificationResult:
    insight_id: str
    statement: str
    category: str
    is_valid: bool
    supporting_facts_count: int
    supporting_sources_count: int
    missing_fact_ids: list[str]
    status: str


@dataclass
class VerificationReport:
    client_id: str
    client_name: str
    verified_at: str
    overall_health_score: float  # 0.0 - 100.0
    total_sources: int
    reachable_sources: int
    total_facts: int
    grounded_facts: int
    unsupported_facts: int
    total_insights: int
    valid_insights: int
    conflicts_detected: list[dict[str, Any]]
    source_health: list[SourceHealth]
    fact_results: list[FactVerificationResult]
    insight_results: list[InsightVerificationResult]
    recommendations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "client_id": self.client_id,
            "client_name": self.client_name,
            "verified_at": self.verified_at,
            "overall_health_score": round(self.overall_health_score, 1),
            "summary": {
                "total_sources": self.total_sources,
                "reachable_sources": self.reachable_sources,
                "total_facts": self.total_facts,
                "grounded_facts": self.grounded_facts,
                "unsupported_facts": self.unsupported_facts,
                "total_insights": self.total_insights,
                "valid_insights": self.valid_insights,
                "conflicts_count": len(self.conflicts_detected),
            },
            "conflicts_detected": self.conflicts_detected,
            "source_health": [asdict(s) for s in self.source_health],
            "fact_results": [asdict(f) for f in self.fact_results],
            "insight_results": [asdict(i) for i in self.insight_results],
            "recommendations": self.recommendations,
        }


class FactVerificationService:
    """Rigorous evidence and fact-checking verification engine for Client Brain."""

    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def __init__(self, db: Session):
        self.db = db
        self.fact_service = FactService(db)

    def check_source_reachability(self, source: Source, timeout: int = 5) -> SourceHealth:
        if not source.url:
            return SourceHealth(
                source_id=source.id,
                url=None,
                source_type=source.source_type.value,
                status="local_only",
                content_length=len(source.raw_reference or ""),
            )

        parsed = urlparse(source.url)
        if not parsed.scheme or not parsed.netloc or parsed.netloc in {"search.index", "localhost"}:
            return SourceHealth(
                source_id=source.id,
                url=source.url,
                source_type=source.source_type.value,
                status="local_only",
                content_length=len(source.raw_reference or ""),
            )

        start_time = datetime.now(timezone.utc)
        try:
            req = urllib.request.Request(
                source.url,
                headers={"User-Agent": self.USER_AGENT, "Accept": "text/html,*/*;q=0.8"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                code = resp.getcode()
                final_url = resp.geturl()
                is_redirected = final_url.rstrip("/") != source.url.rstrip("/")
                return SourceHealth(
                    source_id=source.id,
                    url=source.url,
                    source_type=source.source_type.value,
                    status="redirected" if is_redirected else "reachable",
                    http_code=code,
                    response_time_ms=round(elapsed, 1),
                    content_length=int(resp.headers.get("Content-Length", len(source.raw_reference or ""))),
                )
        except Exception as err:
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            return SourceHealth(
                source_id=source.id,
                url=source.url,
                source_type=source.source_type.value,
                status="unreachable",
                http_code=getattr(err, "code", None),
                response_time_ms=round(elapsed, 1),
                error_message=str(err),
            )

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        words = re.findall(r"[a-zA-Z0-9_-]+", str(text).lower())
        stopwords = {
            "the", "and", "a", "an", "in", "on", "of", "to", "for", "with", "at", "by", "from",
            "is", "are", "was", "were", "it", "this", "that", "these", "those", "or", "as", "be",
        }
        return {w for w in words if len(w) > 2 and w not in stopwords}

    def verify_fact_grounding(self, fact: Fact, sources_map: dict[str, Source]) -> FactVerificationResult:
        notes: list[str] = []
        snippets: list[str] = []
        fact_sources = [sources_map[s.id] for s in fact.sources if s.id in sources_map]

        if not fact_sources:
            return FactVerificationResult(
                fact_id=fact.id,
                category=fact.category,
                key=fact.key,
                value=fact.value_json,
                fact_type=fact.fact_type.value,
                original_confidence=fact.confidence,
                calibrated_confidence=max(0.1, fact.confidence * 0.5),
                grounding_status="UNGROUNDED",
                grounding_score=0.0,
                verified_sources_count=0,
                matching_snippets=[],
                conflicts=[],
                notes=["No valid linked source attached to this fact."],
            )

        # Convert fact value into searchable tokens
        val_str = json.dumps(fact.value_json, ensure_ascii=False) if isinstance(fact.value_json, (dict, list)) else str(fact.value_json)
        fact_tokens = self._tokenize(val_str) | self._tokenize(fact.key)

        best_score = 0.0
        verified_sources = 0

        for src in fact_sources:
            src_corpus = ((src.title or "") + " " + (src.raw_reference or "") + " " + json.dumps(src.metadata_json or {})).lower()
            if not src_corpus.strip():
                continue

            # Check exact substring
            val_clean = val_str.strip('"\'- ').lower()
            if len(val_clean) > 3 and val_clean in src_corpus:
                best_score = max(best_score, 1.0)
                verified_sources += 1
                # Find snippet
                idx = src_corpus.find(val_clean)
                start = max(0, idx - 40)
                end = min(len(src_corpus), idx + len(val_clean) + 40)
                snippets.append(f"[{src.title or src.source_type.value}]: ...{src_corpus[start:end].strip()}...")
                continue

            # Check token overlap
            src_tokens = self._tokenize(src_corpus)
            if fact_tokens:
                overlap = len(fact_tokens & src_tokens)
                ratio = overlap / len(fact_tokens)
                if ratio > best_score:
                    best_score = ratio
                if ratio >= 0.4:
                    verified_sources += 1
                    overlap_sample = list(fact_tokens & src_tokens)[:4]
                    snippets.append(f"[{src.title or src.source_type.value}]: Matched tokens {overlap_sample} (overlap: {int(ratio*100)}%)")

        if best_score >= 0.8:
            status = "STRONG"
            calibrated_conf = min(1.0, max(fact.confidence, 0.9))
            notes.append("Claim strongly verified against source text/infobox.")
        elif best_score >= 0.4:
            status = "MODERATE"
            calibrated_conf = round(fact.confidence * 0.9, 2)
            notes.append("Claim partially corroborated by source keywords.")
        elif best_score > 0.0:
            status = "WEAK"
            calibrated_conf = round(fact.confidence * 0.7, 2)
            notes.append("Weak lexical corroboration found in source corpus.")
        else:
            status = "UNGROUNDED"
            calibrated_conf = round(fact.confidence * 0.4, 2)
            notes.append("Claim text was not found in linked source references.")

        return FactVerificationResult(
            fact_id=fact.id,
            category=fact.category,
            key=fact.key,
            value=fact.value_json,
            fact_type=fact.fact_type.value,
            original_confidence=fact.confidence,
            calibrated_confidence=calibrated_conf,
            grounding_status=status,
            grounding_score=round(best_score, 2),
            verified_sources_count=verified_sources,
            matching_snippets=snippets[:3],
            conflicts=[],
            notes=notes,
        )

    MULTI_INSTANCE_KEYS = {
        "published_heading", "published_page_title", "website_description_claim",
        "linked_official_social_profile", "social_url", "document_text", "notes"
    }

    def detect_conflicts(self, facts: list[Fact]) -> list[dict[str, Any]]:
        conflicts = []
        grouped: dict[tuple[str, str], list[Fact]] = {}
        for f in facts:
            if f.status == RecordStatus.ACTIVE:
                if f.key not in self.MULTI_INSTANCE_KEYS:
                    grouped.setdefault((f.category, f.key), []).append(f)

        for (category, key), items in grouped.items():
            if len(items) > 1:
                values = [f.value_json for f in items]
                unique_values = {json.dumps(v, sort_keys=True) for v in values}
                if len(unique_values) > 1:
                    conflicts.append({
                        "category": category,
                        "key": key,
                        "conflicting_facts_count": len(items),
                        "values": values,
                        "fact_ids": [f.id for f in items],
                        "severity": "HIGH" if category in {"identity", "business", "niche"} else "MEDIUM",
                        "message": f"Multiple active facts with contradictory values found for category '{category}', key '{key}'.",
                    })

        return conflicts

    def verify_insights(self, client_id: str, active_fact_ids: set[str], sources_map: dict[str, Source]) -> list[InsightVerificationResult]:
        insights = list(self.db.scalars(select(Insight).where(Insight.client_id == client_id, Insight.status == RecordStatus.ACTIVE)))
        results = []

        for ins in insights:
            supp_fact_ids = {f.id for f in ins.supporting_facts}
            missing_facts = [fid for fid in supp_fact_ids if fid not in active_fact_ids]
            valid_sources = [s.id for s in ins.supporting_sources if s.id in sources_map]

            is_valid = len(missing_facts) == 0 and len(supp_fact_ids) > 0
            results.append(InsightVerificationResult(
                insight_id=ins.id,
                statement=ins.statement,
                category=ins.category,
                is_valid=is_valid,
                supporting_facts_count=len(supp_fact_ids),
                supporting_sources_count=len(valid_sources),
                missing_fact_ids=missing_facts,
                status="VALID" if is_valid else "UNSUPPORTED",
            ))

        return results

    def run_full_verification(self, client_id: str, check_live_urls: bool = True, update_timestamps: bool = True) -> VerificationReport:
        client = self.db.get(Client, client_id)
        if not client:
            raise ValueError(f"Client '{client_id}' not found")

        sources = list(self.db.scalars(select(Source).where(Source.client_id == client_id)))
        sources_map = {s.id: s for s in sources}
        active_facts = self.fact_service.active(client_id)
        active_fact_ids = {f.id for f in active_facts}

        # 1. Source Health Checks
        source_health_results: list[SourceHealth] = []
        reachable_count = 0
        for src in sources:
            if check_live_urls:
                health = self.check_source_reachability(src)
            else:
                health = SourceHealth(
                    source_id=src.id,
                    url=src.url,
                    source_type=src.source_type.value,
                    status="cached" if src.raw_reference else "unverified",
                    content_length=len(src.raw_reference or ""),
                )
            if health.status in {"reachable", "local_only", "cached"}:
                reachable_count += 1
            source_health_results.append(health)

        # 2. Fact Grounding Checks
        fact_results: list[FactVerificationResult] = []
        now_dt = datetime.now(timezone.utc)
        grounded_count = 0
        unsupported_count = 0

        for fact in active_facts:
            res = self.verify_fact_grounding(fact, sources_map)
            if res.grounding_status in {"STRONG", "MODERATE"}:
                grounded_count += 1
            else:
                unsupported_count += 1

            if update_timestamps:
                fact.last_verified_at = now_dt
                fact.confidence = res.calibrated_confidence

            fact_results.append(res)

        # 3. Conflict Detection
        conflicts = self.detect_conflicts(active_facts)

        # 4. Insight Verification
        insight_results = self.verify_insights(client_id, active_fact_ids, sources_map)
        valid_insights_count = sum(1 for i in insight_results if i.is_valid)

        if update_timestamps:
            self.db.commit()

        # 5. Calculate Overall Health Score (0 - 100)
        total_facts = len(active_facts)
        total_sources = len(sources)
        total_insights = len(insight_results)

        fact_score = (grounded_count / total_facts * 60) if total_facts else 60
        source_score = (reachable_count / total_sources * 25) if total_sources else 25
        insight_score = (valid_insights_count / total_insights * 15) if total_insights else 15
        penalty = min(20, len(conflicts) * 10)
        overall_score = max(0.0, min(100.0, fact_score + source_score + insight_score - penalty))

        # 6. Actionable Recommendations
        recommendations: list[str] = []
        if conflicts:
            recommendations.append(f"Resolve {len(conflicts)} conflicting active fact(s) to guarantee consistent handoffs.")
        if unsupported_count > 0:
            recommendations.append(f"{unsupported_count} fact(s) have weak or missing source grounding. Add official documentation or URLs.")
        unreachable = [s.url for s in source_health_results if s.status == "unreachable" and s.url]
        if unreachable:
            recommendations.append(f"{len(unreachable)} source URL(s) could not be reached over HTTP. Verify domain status.")
        if not recommendations:
            recommendations.append("All client claims and sources verified with high confidence. Ready for YT-Searcher retrieval handoff.")

        return VerificationReport(
            client_id=client.id,
            client_name=client.name,
            verified_at=now_dt.isoformat(),
            overall_health_score=overall_score,
            total_sources=total_sources,
            reachable_sources=reachable_count,
            total_facts=total_facts,
            grounded_facts=grounded_count,
            unsupported_facts=unsupported_count,
            total_insights=total_insights,
            valid_insights=valid_insights_count,
            conflicts_detected=conflicts,
            source_health=source_health_results,
            fact_results=fact_results,
            insight_results=insight_results,
            recommendations=recommendations,
        )
