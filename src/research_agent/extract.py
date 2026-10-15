"""Extract atomic facts from usable documents, with quote verification."""

from __future__ import annotations

import logging
import re

from .config import PROMPTS_DIR, TEMPERATURE
from .llm import call_llm_json
from .models import (
    ExtractedFact,
    FactType,
    SanitisedDocument,
    TriageResult,
    Usability,
)

logger = logging.getLogger(__name__)


def _load_prompt() -> str:
    return (PROMPTS_DIR / "extract.md").read_text(encoding="utf-8")


def _normalise_whitespace(text: str) -> str:
    """Collapse all whitespace to single spaces for quote matching."""
    return re.sub(r"\s+", " ", text).strip()


def _quote_matches(quote: str, body: str) -> bool:
    """Check if a quote appears in the document body (whitespace-normalised)."""
    norm_quote = _normalise_whitespace(quote)
    norm_body = _normalise_whitespace(body)
    if not norm_quote or len(norm_quote) < 5:
        return False
    return norm_quote.lower() in norm_body.lower()


def _build_payload(doc: SanitisedDocument, triage: TriageResult) -> str:
    usability_note = ""
    if triage.usable == Usability.LIMITED:
        usability_note = (
            f"\nNOTE: This document has limited reliability ({triage.reason}). "
            "Extract facts but mark promotional claims as 'promotional_claim' type."
        )

    return f"""Document ID: {doc.id}
Source: {doc.source}
Published: {doc.published}
Source class: {triage.source_class.value}
Reliability: {triage.reliability.value}
{usability_note}

<document>
{doc.body}
</document>"""


def _parse_facts(doc_id: str, data: list | dict) -> list[ExtractedFact]:
    """Parse LLM response into ExtractedFact objects."""
    if isinstance(data, dict):
        data = data.get("facts", [])

    facts = []
    for i, item in enumerate(data):
        try:
            fact = ExtractedFact(
                fact_id=f"{doc_id}_F{i + 1}",
                source_id=doc_id,
                metric=item.get("metric", "unknown"),
                value=str(item.get("value", "")),
                unit=item.get("unit", ""),
                period=item.get("period", ""),
                fact_type=FactType(item.get("fact_type", "reported_figure")),
                statement=item.get("statement", ""),
                quote=item.get("quote", ""),
            )
            facts.append(fact)
        except (ValueError, KeyError) as e:
            logger.warning("%s: failed to parse fact %d: %s", doc_id, i, e)
    return facts


def extract_facts(doc: SanitisedDocument, triage: TriageResult) -> list[ExtractedFact]:
    """Extract facts from a single document and verify quotes."""
    system_prompt = _load_prompt()
    payload = _build_payload(doc, triage)
    data = call_llm_json(system_prompt, payload, temperature=TEMPERATURE["extract"])

    raw_facts = _parse_facts(doc.id, data)
    verified: list[ExtractedFact] = []
    dropped = 0

    for fact in raw_facts:
        if _quote_matches(fact.quote, doc.body):
            verified.append(fact)
        else:
            dropped += 1
            logger.warning(
                "%s: dropped fact '%s' -- quote not found in document",
                doc.id,
                fact.metric,
            )

    logger.info(
        "%s: extracted %d facts (%d dropped for bad quotes)", doc.id, len(verified), dropped
    )
    return verified


def extract_all(
    docs: list[SanitisedDocument],
    triage_results: list[TriageResult],
) -> tuple[list[ExtractedFact], int]:
    """Extract facts from all usable documents."""
    triage_by_id = {t.doc_id: t for t in triage_results}
    all_facts: list[ExtractedFact] = []
    total_dropped = 0

    for doc in docs:
        triage = triage_by_id.get(doc.id)
        if not triage or triage.usable == Usability.EXCLUDED:
            logger.info("%s: skipping (excluded)", doc.id)
            continue

        facts = extract_facts(doc, triage)
        all_facts.extend(facts)

    return all_facts, total_dropped
