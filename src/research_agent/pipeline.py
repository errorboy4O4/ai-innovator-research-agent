"""Pipeline orchestration: ingest, sanitise, triage, extract, reconcile, write, verify."""

from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path

from .config import PROMPTS_DIR, TEMPERATURE
from .extract import extract_all
from .ingest import load_research_pack
from .llm import call_llm, get_model_name
from .models import PipelineTrace
from .reconcile import reconcile
from .sanitize import sanitise_all
from .triage import triage_all
from .verify import verify_and_repair
from .write import (
    _strip_code_fence,
    build_writer_payload,
    write_brief,
    write_brief_baseline,
)

logger = logging.getLogger(__name__)


def _repair_fn_factory(
    ticker: str,
    as_of: str,
    triage_results,
    verified_facts,
    conflicts,
    own_calcs,
    docs,
):
    """Return a repair function that re-calls the writer with defect feedback."""

    def repair(current_brief: str, issues: list[str]) -> str:
        system_prompt = (PROMPTS_DIR / "system_prompt.md").read_text(encoding="utf-8")
        write_prompt = (PROMPTS_DIR / "write_brief.md").read_text(encoding="utf-8")

        payload = build_writer_payload(
            ticker,
            as_of,
            triage_results,
            verified_facts,
            conflicts,
            own_calcs,
            docs,
        )
        defect_list = "\n".join(f"- {i}" for i in issues)
        payload += f"\n\n## Defects found in previous draft (fix all of these):\n{defect_list}"
        payload += f"\n\nPrevious draft:\n{current_brief}"
        payload += (
            "\n\nRewrite the entire brief, fixing all defects listed above. "
            "Ensure the body text (sections 1-4) is strictly between 350 and 430 words."
        )

        return _strip_code_fence(
            call_llm(
                system_prompt + "\n\n" + write_prompt,
                payload,
                temperature=TEMPERATURE["write"],
            )
        )

    return repair


def run_pipeline(
    ticker: str,
    pack_dir: Path,
    as_of: date,
    out_dir: Path,
    variant: str = "full",
) -> tuple[str, PipelineTrace]:
    """Run the full research agent pipeline."""
    as_of_str = as_of.strftime("%d %b %Y")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    trace = PipelineTrace(
        ticker=ticker,
        as_of=as_of_str,
        model=get_model_name(),
        variant=variant,
        timestamp=timestamp,
    )

    # Stage 1: Ingest
    logger.info("=== Stage 1: Ingest ===")
    docs = load_research_pack(pack_dir, as_of)
    trace.documents_loaded = len(docs)

    # Stage 2: Sanitise
    logger.info("=== Stage 2: Sanitise ===")
    sanitised_docs, findings = sanitise_all(docs)
    trace.findings = findings

    if variant == "baseline":
        logger.info("=== Baseline variant: single LLM call ===")
        brief = write_brief_baseline(ticker, as_of_str, sanitised_docs)
        _save_outputs(brief, trace, out_dir, ticker, timestamp)
        return brief, trace

    # Stage 3: Triage
    logger.info("=== Stage 3: Triage ===")
    triage_results = triage_all(sanitised_docs, ticker)
    trace.triage_results = triage_results

    if variant == "triage":
        # Triage variant: triage + extract + write, no reconciliation or verification
        logger.info("=== Stage 4: Extract ===")
        all_facts, dropped = extract_all(sanitised_docs, triage_results)
        trace.facts_extracted = len(all_facts)
        trace.facts_dropped = dropped

        logger.info("=== Stage 6: Write (no reconciliation) ===")
        from .models import VerifiedFact

        verified = [VerifiedFact(fact=f, preferred=True) for f in all_facts]
        brief = write_brief(
            ticker,
            as_of_str,
            triage_results,
            verified,
            [],
            [],
            sanitised_docs,
        )
        _save_outputs(brief, trace, out_dir, ticker, timestamp)
        return brief, trace

    # Stage 4: Extract
    logger.info("=== Stage 4: Extract ===")
    all_facts, dropped = extract_all(sanitised_docs, triage_results)
    trace.facts_extracted = len(all_facts)
    trace.facts_dropped = dropped

    # Stage 5: Reconcile
    logger.info("=== Stage 5: Reconcile ===")
    verified_facts, conflicts, own_calcs = reconcile(all_facts, triage_results)
    trace.conflicts = conflicts

    # Stage 6: Write
    logger.info("=== Stage 6: Write ===")
    brief = write_brief(
        ticker,
        as_of_str,
        triage_results,
        verified_facts,
        conflicts,
        own_calcs,
        sanitised_docs,
    )

    # Stage 7: Verify
    logger.info("=== Stage 7: Verify ===")
    all_source_ids = {d.id for d in docs}
    repair_fn = _repair_fn_factory(
        ticker,
        as_of_str,
        triage_results,
        verified_facts,
        conflicts,
        own_calcs,
        sanitised_docs,
    )
    brief, remaining_issues, repair_count = verify_and_repair(
        brief,
        triage_results,
        all_source_ids,
        repair_fn,
    )
    trace.verification_passed = len(remaining_issues) == 0
    trace.verification_issues = remaining_issues
    trace.repair_attempts = repair_count

    # Word count
    import re

    body = brief
    src_idx = brief.find("## 5. Sources")
    if src_idx > 0:
        body = brief[:src_idx]
    body = re.sub(r"[#*|_\[\](){}]", " ", body)
    trace.brief_word_count = len(body.split())

    _save_outputs(brief, trace, out_dir, ticker, timestamp)
    return brief, trace


def _save_outputs(brief: str, trace: PipelineTrace, out_dir: Path, ticker: str, timestamp: str):
    """Save the brief and trace files."""
    briefs_dir = out_dir / "briefs"
    traces_dir = out_dir / "traces"
    briefs_dir.mkdir(parents=True, exist_ok=True)
    traces_dir.mkdir(parents=True, exist_ok=True)

    brief_path = briefs_dir / f"{ticker}_brief.md"
    brief_path.write_text(brief, encoding="utf-8")
    logger.info("Brief saved to %s", brief_path)

    trace_path = traces_dir / f"{ticker}_{timestamp}.json"
    trace_path.write_text(
        trace.model_dump_json(indent=2),
        encoding="utf-8",
    )
    logger.info("Trace saved to %s", trace_path)


def run_scan(pack_dir: Path, as_of: date):
    """Scan-only mode: ingest and sanitise, no API key needed."""
    docs = load_research_pack(pack_dir, as_of)
    sanitised_docs, findings = sanitise_all(docs)

    print(f"\n{'=' * 60}")
    print(f"SCAN RESULTS: {len(docs)} documents loaded")
    print(f"{'=' * 60}\n")

    for doc in sanitised_docs:
        status = "CLEAN" if not doc.findings else f"{len(doc.findings)} FINDING(S)"
        injection = " [INJECTION DETECTED]" if doc.has_injection else ""
        print(f"  {doc.id} ({doc.filename}): {status}{injection}")

    if findings:
        print("\nDetailed findings:")
        for f in findings:
            print(f"  [{f.doc_id}] {f.kind.value}: {f.excerpt}")
    else:
        print("\nNo findings.")

    return sanitised_docs, findings
