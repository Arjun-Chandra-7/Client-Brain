from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, engine
from app.models import Client
from app.services.brand_analysis_service import BrandAnalysisService
from app.services.export_service import YTExportService
from app.services.verification_service import FactVerificationService, VerificationReport


# ANSI color formatting for terminal
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def print_banner():
    print(f"\n{CYAN}{BOLD}================================================================={RESET}")
    print(f"{CYAN}{BOLD}        VIRALYST CLIENT BRAIN — FACT CHECK & VERIFIER PROGRAM     {RESET}")
    print(f"{CYAN}{BOLD}================================================================={RESET}\n")


def print_report(report: VerificationReport):
    score = report.overall_health_score
    score_color = GREEN if score >= 80 else (YELLOW if score >= 50 else RED)

    print(f"{BOLD}Client:{RESET} {report.client_name} ({DIM}{report.client_id}{RESET})")
    print(f"{BOLD}Audit Timestamp:{RESET} {report.verified_at}")
    print(f"{BOLD}Overall Evidence Health Score:{RESET} {score_color}{score}/100{RESET}\n")

    print(f"{BOLD}─── SUMMARY METRICS ───{RESET}")
    print(f" • Sources Audited:       {report.reachable_sources}/{report.total_sources} active/reachable")
    print(f" • Facts Verified:        {GREEN}{report.grounded_facts} grounded{RESET} / {report.total_facts} total active")
    print(f" • Strategic Inferences:  {report.valid_insights}/{report.total_insights} fully evidence-backed")
    print(f" • Active Conflicts:      {RED if report.conflicts_detected else GREEN}{len(report.conflicts_detected)} conflict(s) detected{RESET}\n")

    if report.conflicts_detected:
        print(f"{RED}{BOLD}─── CONFLICT ALERTS ───{RESET}")
        for conf in report.conflicts_detected:
            print(f" {RED}⚠ [{conf['category']}.{conf['key']}]{RESET} {conf['message']}")
            print(f"   Values: {conf['values']}\n")

    print(f"{BOLD}─── FACT GROUNDING AUDIT (SAMPLE) ───{RESET}")
    for fact in report.fact_results[:12]:
        badge = GREEN + "STRONG" + RESET if fact.grounding_status == "STRONG" else (
            YELLOW + "MODERATE" + RESET if fact.grounding_status == "MODERATE" else (
                RED + fact.grounding_status + RESET
            )
        )
        val_str = str(fact.value)[:60] + ("..." if len(str(fact.value)) > 60 else "")
        print(f" [{badge}] {CYAN}{fact.category}.{fact.key}{RESET}: {val_str}")
        print(f"          {DIM}Confidence: {int(fact.calibrated_confidence*100)}% | Grounding: {int(fact.grounding_score*100)}% | Sources: {fact.verified_sources_count}{RESET}")
        if fact.matching_snippets:
            print(f"          {DIM}Evidence: {fact.matching_snippets[0][:90]}...{RESET}")

    if len(report.fact_results) > 12:
        print(f" {DIM}... and {len(report.fact_results) - 12} more verified facts.{RESET}\n")
    else:
        print()

    print(f"{BOLD}─── SOURCE HEALTH ───{RESET}")
    for src in report.source_health[:6]:
        status_color = GREEN if src.status in {"reachable", "local_only", "cached"} else RED
        url_disp = src.url or f"Local Document ({src.source_type})"
        print(f" • [{status_color}{src.status.upper()}{RESET}] {url_disp} {DIM}({src.response_time_ms or 0}ms){RESET}")
    print()

    print(f"{BOLD}─── ACTIONABLE RECOMMENDATIONS ───{RESET}")
    for rec in report.recommendations:
        print(f" 👉 {rec}")
    print()


def main():
    parser = argparse.ArgumentParser(description="VIRALYST Client Brain Fact Checker & Verifier Program")
    parser.add_argument("--client-id", help="Verify specific client ID")
    parser.add_argument("--brand", help="Verify or research & verify by brand name")
    parser.add_argument("--all", action="store_true", help="Verify all clients in the database")
    parser.add_argument("--no-network", action="store_true", help="Skip live HTTP network checks")
    parser.add_argument("--export-yt", type=Path, help="Export verified client.json to specified path for YT-Searcher")
    parser.add_argument("--json", action="store_true", help="Output raw JSON verification report")

    args = parser.parse_args()
    db: Session = SessionLocal()

    try:
        verifier = FactVerificationService(db)
        exporter = YTExportService(db)

        client_ids = []

        if args.client_id:
            client_ids = [args.client_id]
        elif args.brand:
            client = db.scalars(select(Client).where(Client.name.ilike(f"%{args.brand}%"))).first()
            if not client:
                print(f"{YELLOW}Brand '{args.brand}' not found in local ledger. Running research pipeline first...{RESET}")
                brand_service = BrandAnalysisService(db)
                from app.schemas import BrandAnalysisRequest
                res = brand_service.analyze(BrandAnalysisRequest(brand_name=args.brand))
                client = res["client"]
            client_ids = [client.id]
        elif args.all:
            client_ids = [c.id for c in db.scalars(select(Client)).all()]
            if not client_ids:
                print("No clients found in database.")
                return
        else:
            # Default to the most recent client
            latest = db.scalars(select(Client).order_by(Client.created_at.desc())).first()
            if latest:
                client_ids = [latest.id]
            else:
                print(f"{YELLOW}No clients in database. Pass --brand <name> to research and verify a brand.{RESET}")
                return

        for cid in client_ids:
            report = verifier.run_full_verification(cid, check_live_urls=not args.no_network)
            if args.json:
                print(json.dumps(report.to_dict(), indent=2))
            else:
                print_banner()
                print_report(report)

            if args.export_yt:
                client_json = exporter.build_client_json(cid)
                args.export_yt.parent.mkdir(parents=True, exist_ok=True)
                args.export_yt.write_text(json.dumps(client_json, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                print(f"{GREEN}✓ Successfully exported verified client.json to {args.export_yt} for YT-Searcher!{RESET}\n")

    finally:
        db.close()


if __name__ == "__main__":
    main()
