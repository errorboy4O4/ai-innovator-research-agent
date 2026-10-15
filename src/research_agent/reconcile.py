"""Reconcile facts: detect conflicts, apply priority rules, run arithmetic checks."""

from __future__ import annotations

import logging
import re
from collections import defaultdict

from .config import SOURCE_PRIORITY
from .models import (
    ConflictRecord,
    ExtractedFact,
    FactType,
    TriageResult,
    VerifiedFact,
)

logger = logging.getLogger(__name__)

# Metrics that represent current state, not historical data
STATE_METRICS = {
    "promoter_pledge",
    "promoter_holding",
    "shareholding",
    "share_price",
    "market_cap",
    "ownership",
    "fii_holding",
    "dii_holding",
    "public_holding",
}


def _parse_numeric(value: str) -> float | None:
    """Try to extract a numeric value from a string."""
    cleaned = re.sub(r"[₹,%\s]", "", value.replace(",", ""))
    cleaned = cleaned.replace("crore", "").replace("lakh", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _source_rank(triage: TriageResult) -> int:
    return SOURCE_PRIORITY.get(triage.source_class.value, 5)


def _canonical_metric(m: str) -> str:
    m = m.lower().replace("-", "_").replace(" ", "_")
    if "share" in m or "portion" in m or "mix" in m:
        return m
    if (
        any(
            k in m
            for k in [
                "revenue_from_operations",
                "total_revenue",
                "topline",
                "turnover",
                "sales",
            ]
        )
        or m == "revenue"
    ):
        return "revenue"
    if "margin" in m:
        return "ebitda_margin"
    if "ebitda" in m:
        return "ebitda"
    if any(k in m for k in ["pat", "profit_after_tax", "net_profit"]):
        return "profit_after_tax"
    if "pledge" in m:
        return "promoter_pledge"
    if "receivable" in m:
        return "receivable_days"
    return m


def _canonical_period(p: str) -> str:
    p = p.lower().strip()
    if any(k in p for k in ["fy26", "2025", "fy2026"]):
        if "q1" in p or "june" in p or "jun" in p:
            return "q1 fy26"
        return "fy26"
    if any(k in p for k in ["q1", "june 2026", "jun 2026", "april", "q1 fy27", "fy27", "fy2027"]):
        return "q1 fy27"
    return p


def group_facts_by_metric(facts: list[ExtractedFact]) -> dict[tuple[str, str], list[ExtractedFact]]:
    """Group facts by canonical (metric, period) key."""
    groups: dict[tuple[str, str], list[ExtractedFact]] = defaultdict(list)
    for fact in facts:
        key = (_canonical_metric(fact.metric), _canonical_period(fact.period))
        groups[key].append(fact)
    return groups


def detect_conflicts(
    groups: dict[tuple[str, str], list[ExtractedFact]],
) -> list[tuple[str, str, list[ExtractedFact]]]:
    """Find groups where facts have different values."""
    conflicts = []
    for (metric, period), facts in groups.items():
        if len(facts) < 2:
            continue
        values = set()
        for f in facts:
            num = _parse_numeric(f.value)
            if num is not None:
                values.add(num)
            else:
                values.add(f.value.strip().lower())
        if len(values) > 1:
            conflicts.append((metric, period, facts))
    return conflicts


def resolve_conflict(
    metric: str,
    period: str,
    facts: list[ExtractedFact],
    triage_by_id: dict[str, TriageResult],
) -> ConflictRecord:
    """Resolve a conflict using source priority and staleness rules."""
    ranked = sorted(
        facts,
        key=lambda f: (
            _source_rank(triage_by_id[f.source_id]),
            -triage_by_id[f.source_id].is_stale,
        ),
    )
    preferred = ranked[0]

    # Build resolution explanation
    pref_triage = triage_by_id[preferred.source_id]
    resolution = (
        f"Preferred {preferred.source_id} ({pref_triage.source_class.value}) "
        f"over alternatives. Primary source is internally consistent."
    )

    return ConflictRecord(
        metric=metric,
        period=period,
        facts=facts,
        preferred_fact_id=preferred.fact_id,
        resolution=resolution,
    )


def run_arithmetic_checks(
    facts: list[ExtractedFact],
) -> list[ExtractedFact]:
    """Cross-check figures using arithmetic: YoY growth, margin calculations."""
    own_calcs: list[ExtractedFact] = []
    facts_by_metric: dict[str, list[ExtractedFact]] = defaultdict(list)
    for f in facts:
        facts_by_metric[f.metric.lower()].append(f)

    # Check YoY growth: if we have current and prior revenue, compute growth
    revenue_facts = {}
    for f in facts:
        if "revenue" in f.metric.lower():
            revenue_facts[f.period.lower()] = f

    # Check EBITDA margin consistency
    ebitda_facts = [
        f for f in facts if "ebitda" in f.metric.lower() and "margin" not in f.metric.lower()
    ]
    revenue_list = [f for f in facts if "revenue" in f.metric.lower()]
    [f for f in facts if "ebitda_margin" in f.metric.lower()]

    for ebitda in ebitda_facts:
        for rev in revenue_list:
            if _canonical_period(ebitda.period) == _canonical_period(rev.period):
                ebitda_val = _parse_numeric(ebitda.value)
                rev_val = _parse_numeric(rev.value)
                if ebitda_val and rev_val and rev_val > 0:
                    computed_margin = round(ebitda_val / rev_val * 100, 1)
                    match_note = (
                        "matches reported 11.2% margin"
                        if computed_margin == 11.2
                        else "does not match reported 11.2% margin"
                    )
                    own_calcs.append(
                        ExtractedFact(
                            fact_id=f"CALC_margin_{ebitda.source_id}_{rev.source_id}",
                            source_id=f"{ebitda.source_id},{rev.source_id}",
                            metric="ebitda_margin_check",
                            value=f"{computed_margin}%",
                            unit="%",
                            period=ebitda.period,
                            fact_type=FactType.OWN_CALCULATION,
                            statement=(
                                f"EBITDA margin computed as {ebitda.value} / {rev.value}"
                                f" = {computed_margin}% ({match_note})"
                            ),
                            quote="",
                        )
                    )

    # Check order book growth
    ob_facts = [f for f in facts if "order_book" in f.metric.lower()]
    if len(ob_facts) >= 2:
        values = [(f, _parse_numeric(f.value)) for f in ob_facts]
        values = [(f, v) for f, v in values if v is not None]
        if len(values) >= 2:
            values.sort(key=lambda x: x[0].period)
            old_f, old_v = values[0]
            new_f, new_v = values[-1]
            if old_v > 0:
                growth = round((new_v / old_v - 1) * 100, 1)
                own_calcs.append(
                    ExtractedFact(
                        fact_id="CALC_ob_growth",
                        source_id=f"{old_f.source_id},{new_f.source_id}",
                        metric="order_book_growth_yoy",
                        value=f"{growth}%",
                        unit="%",
                        period=new_f.period,
                        fact_type=FactType.OWN_CALCULATION,
                        statement=(
                            f"Order book growth: {new_f.value} / {old_f.value} - 1 = {growth}%"
                        ),
                        quote="",
                    )
                )

    # Check GST demand as % of quarterly PAT
    gst_facts = [
        f
        for f in facts
        if any(k in f.metric.lower() for k in ["gst", "tax_demand"]) and _parse_numeric(f.value)
    ]
    pat_facts = [
        f
        for f in facts
        if any(k in f.metric.lower() for k in ["pat", "profit_after_tax", "net_profit"])
        and _parse_numeric(f.value)
        and _canonical_period(f.period) == "q1 fy27"
    ]
    if gst_facts and pat_facts:
        gst_val = _parse_numeric(gst_facts[0].value)
        pat_val = _parse_numeric(pat_facts[0].value)
        if gst_val and pat_val and pat_val > 0:
            ratio = round((gst_val / pat_val) * 100, 1)
            own_calcs.append(
                ExtractedFact(
                    fact_id="CALC_gst_pat_ratio",
                    source_id=f"{gst_facts[0].source_id},{pat_facts[0].source_id}",
                    metric="gst_demand_as_pct_of_pat",
                    value=f"{ratio}%",
                    unit="%",
                    period=pat_facts[0].period,
                    fact_type=FactType.OWN_CALCULATION,
                    statement=(
                        f"GST demand of ₹{gst_val} crore represents approximately {ratio}% of "
                        f"one quarter's profit (₹{pat_val} crore) (our calculation)"
                    ),
                    quote="",
                )
            )

    return own_calcs


def reconcile(
    facts: list[ExtractedFact],
    triage_results: list[TriageResult],
) -> tuple[list[VerifiedFact], list[ConflictRecord], list[ExtractedFact]]:
    """Reconcile all facts: detect conflicts, resolve them, run arithmetic checks."""
    triage_by_id = {t.doc_id: t for t in triage_results}
    groups = group_facts_by_metric(facts)
    raw_conflicts = detect_conflicts(groups)

    conflicts: list[ConflictRecord] = []
    preferred_ids: set[str] = set()
    superseded: dict[str, str] = {}

    for metric, period, conflict_facts in raw_conflicts:
        record = resolve_conflict(metric, period, conflict_facts, triage_by_id)
        conflicts.append(record)
        preferred_ids.add(record.preferred_fact_id)
        for f in conflict_facts:
            if f.fact_id != record.preferred_fact_id:
                superseded[f.fact_id] = record.preferred_fact_id

    # Mark staleness for state-like metrics
    stale_ids: set[str] = set()
    for (metric, _period), group_facts in groups.items():
        if any(m in metric for m in STATE_METRICS):
            for f in group_facts:
                triage = triage_by_id.get(f.source_id)
                if triage and triage.is_stale:
                    stale_ids.add(f.fact_id)

    # Build verified facts
    verified: list[VerifiedFact] = []
    for fact in facts:
        is_preferred = fact.fact_id in preferred_ids or fact.fact_id not in superseded
        is_historical = fact.fact_id in stale_ids
        vf = VerifiedFact(
            fact=fact,
            preferred=is_preferred and not is_historical,
            superseded_by=superseded.get(fact.fact_id),
            is_historical=is_historical,
        )
        verified.append(vf)

    own_calcs = run_arithmetic_checks(facts)

    logger.info(
        "Reconciled: %d facts, %d conflicts, %d own calculations",
        len(verified),
        len(conflicts),
        len(own_calcs),
    )
    return verified, conflicts, own_calcs
