"""Triage each document: entity match, source class, reliability, usability."""

from __future__ import annotations

import logging

from .config import PROMPTS_DIR, TEMPERATURE
from .llm import call_llm_json
from .models import (
    Reliability,
    SanitisedDocument,
    SourceClass,
    TriageResult,
    Usability,
)

logger = logging.getLogger(__name__)


def _load_prompt() -> str:
    return (PROMPTS_DIR / "triage.md").read_text(encoding="utf-8")


def _build_payload(doc: SanitisedDocument, ticker: str, company_name: str) -> str:
    findings_text = ""
    if doc.findings:
        findings_text = "\n\nSanitiser findings:\n"
        for f in doc.findings:
            findings_text += f"- {f.kind.value}: {f.excerpt}\n"

    return f"""Target ticker: {ticker}
Target company name: {company_name}

Document ID: {doc.id}
Filename: {doc.filename}
Source: {doc.source}
URL: {doc.url}
Published: {doc.published}
Document type (from front matter): {doc.doc_type}
Age in days: {doc.age_days}
{findings_text}
<document>
{doc.body}
</document>"""


def _parse_triage_response(doc_id: str, data: dict) -> TriageResult:
    return TriageResult(
        doc_id=doc_id,
        entity_match=data.get("entity_match", True),
        entity_note=data.get("entity_note", ""),
        source_class=SourceClass(data.get("source_class", "news")),
        reliability=Reliability(data.get("reliability", "medium")),
        is_stale=data.get("is_stale", False),
        usable=Usability(data.get("usable", "full")),
        reason=data.get("reason", ""),
    )


def _apply_overrides(result: TriageResult, doc: SanitisedDocument) -> TriageResult:
    """Hard code overrides: injection-flagged docs cannot be high reliability or full usability."""
    if doc.has_injection:
        if result.reliability != Reliability.LOW:
            logger.info("%s: overriding reliability to LOW (injection detected)", doc.id)
            result.reliability = Reliability.LOW
        if result.usable == Usability.FULL:
            logger.info("%s: overriding usability to LIMITED (injection detected)", doc.id)
            result.usable = Usability.LIMITED

    if not result.entity_match:
        result.usable = Usability.EXCLUDED
        if not result.reason:
            result.reason = "Document is about a different entity"

    return result


def infer_company_name(docs: list[SanitisedDocument]) -> str:
    """Infer the company name from the primary filing documents."""
    # Look for the company name in official filings first
    for doc in docs:
        if "filing" in doc.doc_type.lower() or "press release" in doc.doc_type.lower():
            # Look for patterns like "Company Ltd" or "Company Limited"
            import re

            match = re.search(r"([\w\s]+(?:Ltd|Limited))\s*\(", doc.body)
            if match:
                return match.group(1).strip()
    return ""


def triage_document(
    doc: SanitisedDocument,
    ticker: str,
    company_name: str,
) -> TriageResult:
    """Triage a single document using the LLM."""
    system_prompt = _load_prompt()
    payload = _build_payload(doc, ticker, company_name)
    data = call_llm_json(system_prompt, payload, temperature=TEMPERATURE["triage"])
    result = _parse_triage_response(doc.id, data)
    result = _apply_overrides(result, doc)
    logger.info(
        "%s: entity=%s class=%s reliability=%s usable=%s (%s)",
        doc.id,
        result.entity_match,
        result.source_class.value,
        result.reliability.value,
        result.usable.value,
        result.reason,
    )
    return result


def triage_all(
    docs: list[SanitisedDocument],
    ticker: str,
) -> list[TriageResult]:
    """Triage all documents, inferring company name from primary filings."""
    company_name = infer_company_name(docs)
    logger.info("Inferred company name: '%s'", company_name)
    results = []
    for doc in docs:
        result = triage_document(doc, ticker, company_name)
        results.append(result)
    return results
