"""Strip hidden content, detect injection attempts, and record findings."""

from __future__ import annotations

import logging
import re

from .config import INJECTION_PATTERNS
from .models import Document, Finding, FindingKind, SanitisedDocument

logger = logging.getLogger(__name__)

# Zero-width Unicode characters that can hide text
ZERO_WIDTH_RE = re.compile(r"[\u200b\u200c\u200d\u2060\ufeff]")

# HTML comments
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)

# Compiled injection patterns
_INJECTION_RES = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


def _find_html_comments(doc_id: str, body: str) -> tuple[str, list[Finding]]:
    """Remove HTML comments and record each one as a finding."""
    findings: list[Finding] = []
    for match in HTML_COMMENT_RE.finditer(body):
        excerpt = match.group()
        if len(excerpt) > 200:
            excerpt = excerpt[:200] + "..."
        findings.append(
            Finding(
                doc_id=doc_id,
                kind=FindingKind.HTML_COMMENT,
                excerpt=excerpt,
                location=f"chars {match.start()}-{match.end()}",
            )
        )
    cleaned = HTML_COMMENT_RE.sub("", body)
    return cleaned, findings


def _find_zero_width(doc_id: str, body: str) -> tuple[str, list[Finding]]:
    """Remove zero-width characters and record findings."""
    findings: list[Finding] = []
    matches = list(ZERO_WIDTH_RE.finditer(body))
    if matches:
        findings.append(
            Finding(
                doc_id=doc_id,
                kind=FindingKind.ZERO_WIDTH_CHAR,
                excerpt=f"{len(matches)} zero-width characters found",
                location="throughout document",
            )
        )
    cleaned = ZERO_WIDTH_RE.sub("", body)
    return cleaned, findings


def _scan_injection(doc_id: str, body: str) -> list[Finding]:
    """Scan for injection phrases without removing them (they are signals, not the only defence)."""
    findings: list[Finding] = []
    for pattern_re in _INJECTION_RES:
        for match in pattern_re.finditer(body):
            excerpt = body[max(0, match.start() - 30) : match.end() + 30]
            findings.append(
                Finding(
                    doc_id=doc_id,
                    kind=FindingKind.INJECTION_PHRASE,
                    excerpt=excerpt.strip(),
                    location=f"chars {match.start()}-{match.end()}",
                )
            )
    return findings


def sanitise_document(doc: Document) -> SanitisedDocument:
    """Clean a document and scan for injection attempts."""
    all_findings: list[Finding] = []

    body, comment_findings = _find_html_comments(doc.id, doc.body)
    all_findings.extend(comment_findings)

    body, zw_findings = _find_zero_width(doc.id, body)
    all_findings.extend(zw_findings)

    injection_findings = _scan_injection(doc.id, doc.body)
    all_findings.extend(injection_findings)

    has_injection = any(f.kind == FindingKind.INJECTION_PHRASE for f in all_findings)

    if all_findings:
        logger.warning(
            "%s: %d findings (%s)",
            doc.id,
            len(all_findings),
            ", ".join(f.kind.value for f in all_findings),
        )

    return SanitisedDocument(
        id=doc.id,
        filename=doc.filename,
        source=doc.source,
        url=doc.url,
        published=doc.published,
        doc_type=doc.doc_type,
        body=body,
        original_body=doc.body,
        age_days=doc.age_days,
        findings=all_findings,
        has_injection=has_injection,
    )


def sanitise_all(docs: list[Document]) -> tuple[list[SanitisedDocument], list[Finding]]:
    """Sanitise all documents, returning cleaned docs and a flat findings list."""
    all_findings: list[Finding] = []
    sanitised: list[SanitisedDocument] = []

    for doc in docs:
        sdoc = sanitise_document(doc)
        sanitised.append(sdoc)
        all_findings.extend(sdoc.findings)

    return sanitised, all_findings
