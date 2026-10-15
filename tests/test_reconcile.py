"""Tests for the reconcile module: conflict detection and arithmetic checks."""

from datetime import date

from research_agent.models import (
    ExtractedFact,
    FactType,
    Reliability,
    SourceClass,
    TriageResult,
    Usability,
)
from research_agent.reconcile import (
    detect_conflicts,
    group_facts_by_metric,
    resolve_conflict,
    run_arithmetic_checks,
)


def _fact(
    source_id: str, metric: str, value: str, period: str = "Q1 FY27", fact_id: str = ""
) -> ExtractedFact:
    return ExtractedFact(
        fact_id=fact_id or f"{source_id}_{metric}",
        source_id=source_id,
        metric=metric,
        value=value,
        unit="₹ crore",
        period=period,
        fact_type=FactType.REPORTED_FIGURE,
        statement=f"{metric} is {value}",
        quote=f"{metric} {value}",
    )


def _triage(
    doc_id: str,
    source_class: str = "official_filing",
    reliability: str = "high",
    is_stale: bool = False,
    published: date | None = None,
) -> TriageResult:
    return TriageResult(
        doc_id=doc_id,
        entity_match=True,
        entity_note="",
        source_class=SourceClass(source_class),
        reliability=Reliability(reliability),
        is_stale=is_stale,
        usable=Usability.FULL,
        reason="",
        published=published,
    )


def test_group_facts_by_metric():
    facts = [
        _fact("S1", "revenue", "1248"),
        _fact("S2", "revenue", "1428"),
        _fact("S1", "ebitda", "140"),
    ]
    groups = group_facts_by_metric(facts)
    assert len(groups[("revenue", "q1 fy27")]) == 2
    assert len(groups[("ebitda", "q1 fy27")]) == 1


def test_detect_conflicts():
    facts = [
        _fact("S1", "revenue", "1248"),
        _fact("S2", "revenue", "1428"),
    ]
    groups = group_facts_by_metric(facts)
    conflicts = detect_conflicts(groups)
    assert len(conflicts) == 1
    assert conflicts[0][0] == "revenue"


def test_no_conflict_same_value():
    facts = [
        _fact("S1", "pat", "82"),
        _fact("S2", "pat", "82"),
    ]
    groups = group_facts_by_metric(facts)
    conflicts = detect_conflicts(groups)
    assert len(conflicts) == 0


def test_resolve_conflict_prefers_primary():
    facts = [
        _fact("S3", "revenue", "1248", fact_id="S3_rev"),
        _fact("S1", "revenue", "1428", fact_id="S1_rev"),
    ]
    triage_by_id = {
        "S3": _triage("S3", "official_filing", "high"),
        "S1": _triage("S1", "news", "medium"),
    }
    record = resolve_conflict("revenue", "Q1 FY27", facts, triage_by_id)
    assert record.preferred_fact_id == "S3_rev"


def test_arithmetic_check_ebitda_margin():
    facts = [
        _fact("S1", "ebitda", "140"),
        _fact("S1", "revenue", "1248"),
    ]
    calcs = run_arithmetic_checks(facts)
    margin_calcs = [c for c in calcs if "margin" in c.metric]
    assert len(margin_calcs) == 1
    assert "11.2" in margin_calcs[0].value


def test_arithmetic_check_with_wrong_revenue():
    """If revenue were 1428, the margin would be ~9.8%, not the reported 11.2%."""
    facts = [
        _fact("S1", "ebitda", "140"),
        _fact("S2", "revenue", "1428"),
    ]
    calcs = run_arithmetic_checks(facts)
    margin_calcs = [c for c in calcs if "margin" in c.metric]
    assert len(margin_calcs) == 1
    assert "9.8" in margin_calcs[0].value


def test_resolve_conflict_prefers_non_stale_over_stale_in_same_tier():
    facts = [
        _fact("S_stale", "promoter_pledge", "35%", fact_id="f_stale"),
        _fact("S_fresh", "promoter_pledge", "4.1%", fact_id="f_fresh"),
    ]
    triage_by_id = {
        "S_stale": _triage("S_stale", "news", "medium", is_stale=True, published=date(2024, 3, 18)),
        "S_fresh": _triage("S_fresh", "news", "medium", is_stale=False, published=date(2026, 8, 9)),
    }
    record = resolve_conflict("promoter_pledge", "Q1 FY27", facts, triage_by_id)
    assert record.preferred_fact_id == "f_fresh"


def test_resolve_conflict_prefers_more_recent_date():
    facts = [
        _fact("S_older", "capex", "100", fact_id="f_old"),
        _fact("S_newer", "capex", "120", fact_id="f_new"),
    ]
    triage_by_id = {
        "S_older": _triage("S_older", "news", "medium", published=date(2026, 7, 1)),
        "S_newer": _triage("S_newer", "news", "medium", published=date(2026, 8, 15)),
    }
    record = resolve_conflict("capex", "FY27", facts, triage_by_id)
    assert record.preferred_fact_id == "f_new"


def test_order_book_chronological_sort():
    facts = [
        _fact("S1", "order_book", "3900", period="30 June 2026"),
        _fact("S2", "order_book", "3150", period="30 June 2025"),
    ]
    calcs = run_arithmetic_checks(facts)
    ob_calcs = [c for c in calcs if "order_book" in c.metric]
    assert len(ob_calcs) == 1
    assert "23.8%" in ob_calcs[0].value
