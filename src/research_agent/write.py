"""Generate the research brief from the verified fact table."""

from __future__ import annotations

import logging

from .config import PROMPTS_DIR, TEMPERATURE
from .llm import call_llm
from .models import (
    ConflictRecord,
    ExtractedFact,
    SanitisedDocument,
    TriageResult,
    VerifiedFact,
)

logger = logging.getLogger(__name__)


def _load_system_prompt() -> str:
    return (PROMPTS_DIR / "system_prompt.md").read_text(encoding="utf-8")


def _load_write_prompt() -> str:
    return (PROMPTS_DIR / "write_brief.md").read_text(encoding="utf-8")


def _format_triage_table(triage_results: list[TriageResult], docs: list[SanitisedDocument]) -> str:
    doc_map = {d.id: d for d in docs}
    lines = [
        "| ID | Source | Date | Type | Reliability | Usable | Reason |",
        "|---|---|---|---|---|---|---|",
    ]
    for t in triage_results:
        doc = doc_map.get(t.doc_id)
        source = doc.source if doc else "Unknown"
        date = str(doc.published) if doc else "Unknown"
        lines.append(
            f"| {t.doc_id} | {source} | {date} | {t.source_class.value} | "
            f"{t.reliability.value} | {t.usable.value} | {t.reason} |"
        )
    return "\n".join(lines)


def _format_fact_table(verified_facts: list[VerifiedFact], own_calcs: list[ExtractedFact]) -> str:
    lines = []
    for vf in verified_facts:
        if not vf.preferred:
            continue
        f = vf.fact
        tag = "(historical)" if vf.is_historical else ""
        lines.append(
            f"- [{f.source_id}] {f.metric}: {f.value} {f.unit} ({f.period}) "
            f"[{f.fact_type.value}] {tag}".strip()
        )

    if own_calcs:
        lines.append("\nOwn calculations:")
        for f in own_calcs:
            lines.append(f"- [{f.source_id}] {f.metric}: {f.value} -- {f.statement}")

    return "\n".join(lines)


def _format_conflicts(conflicts: list[ConflictRecord]) -> str:
    if not conflicts:
        return "No conflicts detected."
    lines = []
    for c in conflicts:
        lines.append(f"\nConflict: {c.metric} ({c.period})")
        for f in c.facts:
            preferred = " ← PREFERRED" if f.fact_id == c.preferred_fact_id else ""
            lines.append(f"  - [{f.source_id}] {f.value} {f.unit}{preferred}")
        lines.append(f"  Resolution: {c.resolution}")
    return "\n".join(lines)


def _format_findings_summary(docs: list[SanitisedDocument]) -> str:
    lines = []
    for doc in docs:
        if doc.findings:
            for finding in doc.findings:
                lines.append(
                    f"- {doc.id} ({doc.filename}): {finding.kind.value} -- {finding.excerpt}"
                )
    return "\n".join(lines) if lines else "No security findings."


def build_writer_payload(
    ticker: str,
    as_of: str,
    triage_results: list[TriageResult],
    verified_facts: list[VerifiedFact],
    conflicts: list[ConflictRecord],
    own_calcs: list[ExtractedFact],
    docs: list[SanitisedDocument],
) -> str:
    """Assemble the payload for the writer LLM. Never includes raw documents."""
    triage_table = _format_triage_table(triage_results, docs)
    fact_table = _format_fact_table(verified_facts, own_calcs)
    conflict_text = _format_conflicts(conflicts)
    findings_text = _format_findings_summary(docs)

    # Collect management claims separately
    mgmt_claims = []
    for vf in verified_facts:
        if vf.fact.fact_type.value == "management_claim" and vf.preferred:
            mgmt_claims.append(f"- [{vf.fact.source_id}] {vf.fact.statement}")
    mgmt_text = "\n".join(mgmt_claims) if mgmt_claims else "None extracted."

    # Collect superseded facts for open questions
    superseded_facts = []
    for vf in verified_facts:
        if vf.superseded_by:
            superseded_facts.append(
                f"- [{vf.fact.source_id}] {vf.fact.metric}: {vf.fact.value} "
                f"(superseded by {vf.superseded_by})"
            )
    superseded_text = "\n".join(superseded_facts) if superseded_facts else "None."

    return f"""Ticker: {ticker}
As-of date: {as_of}

## Source triage table
{triage_table}

## Verified fact table (preferred facts only)
{fact_table}

## Management claims (must be attributed)
{mgmt_text}

## Conflicts detected
{conflict_text}

## Superseded facts (mention in Open questions if material)
{superseded_text}

## Security findings
{findings_text}

Write the research brief now, following the output skeleton exactly."""


def write_brief(
    ticker: str,
    as_of: str,
    triage_results: list[TriageResult],
    verified_facts: list[VerifiedFact],
    conflicts: list[ConflictRecord],
    own_calcs: list[ExtractedFact],
    docs: list[SanitisedDocument],
) -> str:
    """Generate the research brief using the LLM writer."""
    system_prompt = _load_system_prompt()
    write_prompt = _load_write_prompt()
    full_system = system_prompt + "\n\n" + write_prompt

    payload = build_writer_payload(
        ticker,
        as_of,
        triage_results,
        verified_facts,
        conflicts,
        own_calcs,
        docs,
    )

    brief = call_llm(full_system, payload, temperature=TEMPERATURE["write"])
    logger.info("Brief generated (%d chars)", len(brief))
    return brief


def write_brief_baseline(
    ticker: str,
    as_of: str,
    docs: list[SanitisedDocument],
) -> str:
    """Baseline variant: one LLM call with all raw documents, minimal prompt."""
    system_prompt = (
        "You are a research analyst. Write a one-page research brief for a retail investor. "
        "Include sections: Snapshot, Bull case, Bear case, Open questions, Sources. "
        f"Today is {as_of}. Tag claims with source IDs."
    )
    doc_text = ""
    for doc in docs:
        doc_text += (
            f"\n\n--- Document {doc.id}: {doc.filename} (from {doc.source}, {doc.published}) ---\n"
        )
        doc_text += doc.body

    payload = f"Ticker: {ticker}\n\nDocuments:\n{doc_text}\n\nWrite the research brief."
    return call_llm(system_prompt, payload, temperature=0.3)
