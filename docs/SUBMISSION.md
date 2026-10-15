# Submission Deliverables (Form-Ready Blocks)

This file contains the exact text blocks ready to be pasted into the Super Investing Part B assignment submission form.

---

## 1. Link to Build

- **GitHub Repository:** `https://github.com/errorboy4O4/ai-innovator-research-agent`
- **System Prompt File:** `prompts/system_prompt.md`
- **README File:** `README.md`

*(GitHub repository is public and ready for review.)*

---

## 2. Research Brief for Sarvottam Cables Ltd (SRVCABLE)

```markdown
# Sarvottam Cables Ltd (SRVCABLE): research brief
*As of 23 Sep 2026. For information only; this is not investment advice.*

## 1. Snapshot
Sarvottam Cables Ltd manufactures and supplies cables. For Q1 FY27, the company reported revenue from operations of ₹1,248 crore, EBITDA (earnings before interest, tax, depreciation, and amortisation) of ₹140 crore, and a profit after tax of ₹82 crore [S3]. The order book stood at ₹3,900 crore as of 30 June 2026 [S3].

## 2. Bull case
- The order book grew by 23.8% year-on-year to reach ₹3,900 crore as of 30 June 2026 compared to ₹3,150 crore in the previous year [S3].
- Export revenue share increased to 21% of total revenue in Q1 FY27 from 16% in Q1 FY26 [S3].
- Management states that the upcoming Bharuch plant expansion will add about 30% to cable manufacturing capacity by Q3 FY27 [S3].
- Foreign institutional investor holding increased to 11.8% in June 2026 from 9.2% in June 2025, alongside a decline in pledged promoter shares to 4.1% [S8].

## 3. Bear case
- Raw material costs increased by 14% in Q1 FY27, contributing to a contraction in EBITDA margin to 11.2% from 12.9% in Q1 FY26 [S1, S3].
- Receivable days lengthened to 96 days as of June 2026 compared to 78 days in June 2025 [S2].
- The company faces a GST (goods and services tax) demand of ₹46.3 crore for FY2020-21 and FY2021-22, which represents approximately 56.5% of one quarter's profit [S7, (our calculation)].
- Pledged promoter shares, while decreasing, still stand at 4.1% of total shares as of June 2026 [S8].

## 4. Open questions
- Discrepancies exist between news reports and official company filings regarding Q1 FY27 revenue (reported as ₹1,428 crore in [S1] versus ₹1,248 crore in official filing [S3]). Official filing figures were used as they are internally consistent with reported margins.
- Management maintains full-year FY27 revenue growth guidance of 15% to 17% [S2], which remains an unverified forecast.
- Management states that the GST demand of ₹46.3 crore will have no material impact [S7], but independent verification is pending.
- Document S5 was excluded due to an attempted prompt injection and promotional manipulation [S5].
- Source S4 was excluded from current state analysis because it is older than 365 days [S4].
- Source S6 was excluded as it refers to a different legal entity (a local cable TV operator) [S6].

## 5. Sources
| ID | Publisher | Date | Type | Used for | Reliability |
|---|---|---|---|---|---|
| S1 | Business Daily Online | 2026-08-09 | news | Q1 revenue growth, raw material cost, share price | medium (superseded by official filing for financials) |
| S2 | Company IR Site | 2026-08-11 | official_transcript | Management guidance, receivable days, capex | high |
| S3 | Sarvottam Cables Ltd IR | 2026-08-08 | official_filing | Q1 revenue, EBITDA, PAT, order book, exports | high |
| S4 | Market Watch India | 2024-03-18 | news | Historical context | limited (older than 365 days) |
| S5 | MultibaggerAlertsIndia | 2026-08-12 | blog | None (excluded) | low (promotional content with prompt injection) |
| S6 | Nagpur City Times | 2026-08-20 | news | None (excluded) | excluded (wrong entity: local cable TV operator) |
| S7 | NSE corporate announcement | 2026-09-02 | official_filing | GST demand details | high |
| S8 | NSE shareholding pattern | 2026-07-15 | official_filing | Shareholding and pledge data | high |
```

**Edited by hand:** none

---

## 3. Test Log (Condensed Summary)

We developed and evaluated the research agent across three iterations:

1. **Run 1 (Baseline):** A naive single-call architecture without sanitisation or triage. It failed 6 of 13 evaluation traps: it fell for the hidden prompt injection in the blog [S5] by quoting target prices and positive analyst consensus; confused legal entities by citing an ₹8 lakh municipal penalty on a local cable TV operator [S6]; reported a stale 35% promoter pledge from 2024 [S4]; and repeated a conflicting 35% revenue jump [S1].
2. **Run 2 (Triage & Fact Extraction):** Added an HTML comment/regex sanitiser (`sanitize.py`), per-document LLM triage (`triage.py`), and atomic fact extraction with exact substring quote verification (`extract.py`). This eliminated prompt injection vulnerabilities, excluded the irrelevant entity [S6], and recognized source staleness. However, the revenue conflict (₹1,428 cr vs ₹1,248 cr) was merely listed without mathematical cross-check, and management claims lacked explicit attribution.
3. **Run 3 (Full Pipeline):** Implemented deterministic conflict reconciliation and arithmetic checks (`reconcile.py`), automated code verification (`verify.py`), and an LLM critic repair loop. The arithmetic cross-check verified that ₹140 crore EBITDA matches the 11.2% margin only at ₹1,248 crore (primary filing [S3]), resolving the conflict and flagging the discrepancy in Open Questions. Management claims were explicitly attributed, GST demand materiality was calculated (56% of quarterly PAT), and 13 of 13 evaluation traps were handled with 0 code verification issues.

Full details and comparative tables are available in [`docs/TEST_LOG.md`](docs/TEST_LOG.md).

---

## 4. Screen Recording

- **Video URL:** `<RECORDING_URL_PLACEHOLDER>`
- **Duration:** 2 to 3 minutes
- **Script Followed:** [`docs/RECORDING_SCRIPT.md`](docs/RECORDING_SCRIPT.md)
