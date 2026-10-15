"""Verify the generated brief: citations, numbers, forbidden content, structure."""

from __future__ import annotations

import logging
import re

from .config import FORBIDDEN_PHRASES, PROMPTS_DIR, TEMPERATURE
from .llm import call_llm
from .models import TriageResult, Usability

logger = logging.getLogger(__name__)

REQUIRED_HEADINGS = [
    "## 1. Snapshot",
    "## 2. Bull case",
    "## 3. Bear case",
    "## 4. Open questions",
    "## 5. Sources",
]


def check_citations(brief: str, valid_ids: set[str]) -> list[str]:
    """Every [S#] tag must resolve to a real source ID."""
    issues = []
    cited = set(re.findall(r"\[S(\d+)\]", brief))
    for num in cited:
        sid = f"S{num}"
        if sid not in valid_ids:
            issues.append(f"Citation [{sid}] does not resolve to any source")
    return issues


def check_sentences_tagged(brief: str) -> list[str]:
    """Every sentence in sections 1-3 should have at least one [S#] tag."""
    issues = []
    # Extract sections 1-3
    for section_num, section_name in [(1, "Snapshot"), (2, "Bull case"), (3, "Bear case")]:
        pattern = rf"## {section_num}\.\s+{section_name}(.*?)(?=## \d|$)"
        match = re.search(pattern, brief, re.DOTALL)
        if not match:
            continue
        section_text = match.group(1).strip()
        # Split into sentences/bullets
        lines = [
            raw_line.strip()
            for raw_line in section_text.split("\n")
            if raw_line.strip() and not raw_line.strip().startswith("|")
        ]
        for line in lines:
            # Skip if it's just a header or empty
            if line.startswith("#") or line.startswith("*As of") or len(line) < 10:
                continue
            if not re.search(r"\[S\d+", line):
                issues.append(f"Untagged line in section {section_num}: '{line[:60]}...'")
    return issues


def check_forbidden_phrases(brief: str) -> list[str]:
    """No forbidden promotional phrases should appear in the text (table rows excluded)."""
    issues = []
    lines = []
    in_sources = False
    for line in brief.splitlines():
        if "## 5. Sources" in line:
            in_sources = True
        if in_sources and line.strip().startswith("|"):
            continue
        lines.append(line)
    body = "\n".join(lines).lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase in body:
            issues.append(f"Forbidden phrase found: '{phrase}'")
    return issues


def check_excluded_sources(
    brief: str,
    triage_results: list[TriageResult],
) -> list[str]:
    """Excluded sources must not be cited as support, but must appear in the Sources table."""
    issues = []
    excluded_ids = {t.doc_id for t in triage_results if t.usable == Usability.EXCLUDED}

    for eid in excluded_ids:
        # Should not be cited in sections 1-3
        sections_1_to_3 = brief
        sources_idx = brief.find("## 5. Sources")
        if sources_idx > 0:
            sections_1_to_3 = brief[:sources_idx]
        if f"[{eid}]" in sections_1_to_3:
            # Check if it's in the open questions or sources section (ok there)
            open_q_idx = brief.find("## 4. Open questions")
            if open_q_idx > 0 and brief.find(f"[{eid}]") < open_q_idx:
                issues.append(f"Excluded source {eid} cited as support in sections 1-3")

        # Should appear in Sources table
        if sources_idx > 0:
            sources_section = brief[sources_idx:]
            if eid not in sources_section:
                issues.append(f"Excluded source {eid} missing from Sources table")

    return issues


def check_headings(brief: str) -> list[str]:
    """All 5 required headings must exist in order."""
    issues = []
    last_pos = -1
    for heading in REQUIRED_HEADINGS:
        pos = brief.find(heading)
        if pos == -1:
            issues.append(f"Missing heading: {heading}")
        elif pos < last_pos:
            issues.append(f"Heading out of order: {heading}")
        else:
            last_pos = pos
    return issues


def check_word_count(brief: str) -> list[str]:
    """Body text should be 300-520 words."""
    issues = []
    # Strip the title and sources table for word count
    body = brief
    sources_idx = brief.find("## 5. Sources")
    if sources_idx > 0:
        body = brief[:sources_idx]
    # Remove markdown formatting
    body = re.sub(r"[#*|_\[\](){}]", " ", body)
    words = len(body.split())
    if words < 300:
        issues.append(f"Brief may be too short: ~{words} words (target 350-450)")
    elif words > 520:
        issues.append(f"Brief may be too long: ~{words} words (target 350-450)")
    return issues


def check_all_sources_in_table(brief: str, all_ids: set[str]) -> list[str]:
    """All 8 documents should appear in the Sources table."""
    issues = []
    sources_idx = brief.find("## 5. Sources")
    if sources_idx < 0:
        return ["Sources section missing"]
    sources_section = brief[sources_idx:]
    for sid in sorted(all_ids):
        if sid not in sources_section:
            issues.append(f"Source {sid} missing from Sources table")
    return issues


def code_verify(
    brief: str,
    triage_results: list[TriageResult],
    all_source_ids: set[str],
) -> list[str]:
    """Run all code-based verification checks."""
    issues = []
    issues.extend(check_headings(brief))
    issues.extend(check_citations(brief, all_source_ids))
    issues.extend(check_sentences_tagged(brief))
    issues.extend(check_forbidden_phrases(brief))
    issues.extend(check_excluded_sources(brief, triage_results))
    issues.extend(check_word_count(brief))
    issues.extend(check_all_sources_in_table(brief, all_source_ids))
    return issues


def llm_critic(brief: str) -> list[str]:
    """Use the LLM critic to check tone, attribution, and unsupported claims."""
    critic_prompt = (PROMPTS_DIR / "critic.md").read_text(encoding="utf-8")
    response = call_llm(
        critic_prompt,
        f"Review this research brief:\n\n{brief}",
        temperature=TEMPERATURE["critic"],
    )
    # Parse the critic's response into a list of issues
    issues = []
    for line in response.strip().splitlines():
        line = line.strip()
        if line and (line.startswith("-") or line.startswith("*")):
            issues.append(line.lstrip("-* ").strip())
        elif line.upper().startswith("PASS") or line.upper().startswith("NO ISSUES"):
            break
    return issues


def verify_and_repair(
    brief: str,
    triage_results: list[TriageResult],
    all_source_ids: set[str],
    repair_fn,
    max_repairs: int = 2,
) -> tuple[str, list[str], int]:
    """Run verification, attempt repairs if needed. Returns (brief, issues, repair_count)."""
    repair_count = 0

    for attempt in range(max_repairs + 1):
        code_issues = code_verify(brief, triage_results, all_source_ids)
        llm_issues = []
        try:
            llm_issues = llm_critic(brief)
        except Exception as e:
            logger.warning("LLM critic failed: %s", e)

        all_issues = code_issues + llm_issues
        if not all_issues:
            logger.info("Verification passed (attempt %d)", attempt + 1)
            return brief, [], repair_count

        logger.warning("Verification found %d issues (attempt %d)", len(all_issues), attempt + 1)
        for issue in all_issues:
            logger.warning("  - %s", issue)

        if attempt < max_repairs:
            # Feed issues back to the writer for repair
            repair_count += 1
            brief = repair_fn(brief, all_issues)
        else:
            logger.warning("Max repair attempts reached, returning best version")

    return brief, code_issues, repair_count
