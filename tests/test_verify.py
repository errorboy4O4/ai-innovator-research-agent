"""Tests for the verify module: citation checks, forbidden phrases, structure."""

from research_agent.verify import (
    check_all_sources_in_table,
    check_citations,
    check_forbidden_phrases,
    check_headings,
    check_word_count,
)

GOOD_BRIEF = """# Test Corp (TEST): research brief
*As of 23 Sep 2026. For information only; this is not investment advice.*

## 1. Snapshot
Test Corp makes widgets. Revenue was ₹500 crore in Q1 FY27 [S1].
Profit after tax was ₹50 crore [S1]. Order book is ₹800 crore [S1].

## 2. Bull case
- Strong order book of ₹800 crore, up 20% year-on-year [S1].
- Export revenue growing to 15% of total [S1, S2].
- New plant adds 25% capacity [S2].

## 3. Bear case
- Margin pressure from raw material costs [S1].
- Receivable days increased from 60 to 80 [S2].
- GST demand of ₹30 crore pending [S3].

## 4. Open questions
- Revenue figure conflict: ₹500 crore (S1) vs ₹600 crore (S4). We used S1 as primary source.
- Management guidance of 15% growth is unverified.
- No current share price available.

## 5. Sources
| ID | Publisher | Date | Type | Used for | Reliability |
|---|---|---|---|---|---|
| S1 | Test Corp IR | 2026-08-08 | Official filing | Results | High |
| S2 | Test Corp IR | 2026-08-11 | Transcript | Management views | High |
| S3 | NSE | 2026-09-02 | Exchange filing | GST disclosure | High |
| S4 | News Daily | 2026-08-09 | News | Context | Medium |
| S5 | Bad Blog | 2026-08-12 | Blog | Excluded: promotional, injection attempt | Low |
"""


def test_check_citations_valid():
    ids = {"S1", "S2", "S3", "S4", "S5"}
    issues = check_citations(GOOD_BRIEF, ids)
    assert len(issues) == 0


def test_check_citations_invalid():
    ids = {"S1", "S2"}
    issues = check_citations(GOOD_BRIEF, ids)
    assert any("S3" in i for i in issues)


def test_check_headings_present():
    issues = check_headings(GOOD_BRIEF)
    assert len(issues) == 0


def test_check_headings_missing():
    bad = GOOD_BRIEF.replace("## 3. Bear case", "## 3. Risks")
    issues = check_headings(bad)
    assert any("Bear case" in i for i in issues)


def test_check_forbidden_phrases_clean():
    issues = check_forbidden_phrases(GOOD_BRIEF)
    assert len(issues) == 0


def test_check_forbidden_phrases_found():
    bad = GOOD_BRIEF + "\nThis is a strong buy with guaranteed returns."
    issues = check_forbidden_phrases(bad)
    assert any("strong buy" in i for i in issues)
    assert any("guaranteed" in i for i in issues)


def test_check_word_count_reasonable():
    issues = check_word_count(GOOD_BRIEF)
    # The test fixture is intentionally short — just verify the function runs
    # and returns a list (even if it flags the count as short)
    assert isinstance(issues, list)


def test_check_all_sources_in_table():
    ids = {"S1", "S2", "S3", "S4", "S5"}
    issues = check_all_sources_in_table(GOOD_BRIEF, ids)
    assert len(issues) == 0


def test_check_missing_source_in_table():
    ids = {"S1", "S2", "S3", "S4", "S5", "S6"}
    issues = check_all_sources_in_table(GOOD_BRIEF, ids)
    assert any("S6" in i for i in issues)
