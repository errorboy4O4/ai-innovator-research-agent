# AI Research Agent (Super Investing Take-Home Assignment)

An evidence-bound AI research agent that ingests scraped documents about an NSE-listed company and synthesises a one-page, source-grounded Markdown research brief for retail investors. It defends against prompt injections, resolves contradictory numbers using source hierarchies and arithmetic cross-checks, discounts stale data, and excludes unrelated corporate entities.

---

## 1. Quick Start

### Prerequisites
- Python 3.11+
- A Google Gemini API key (free tier eligible)

### Setup
```bash
# 1. Clone repository
git clone https://github.com/errorboy4O4/ai-innovator-research-agent.git
cd sarvottam-research-agent

# 2. Create and activate a virtual environment
python -m venv .venv
# On Linux/macOS:
source .venv/bin/activate
# On Windows PowerShell:
.venv\Scripts\Activate.ps1

# 3. Install dependencies and the package
pip install -r requirements.txt
pip install -e .

# 4. Set up environment variables
cp .env.example .env
# Edit .env and paste your GEMINI_API_KEY
```

---

## 2. Running the Agent

### Scan Mode (Offline / No API Key Needed)
Quickly inspect documents for prompt injection phrases, HTML comments, and hidden zero-width characters:
```bash
research-agent scan --pack data/research_pack
# Or run with the dry-run flag:
research-agent run --ticker SRVCABLE --pack data/research_pack --dry-run
```

### Full Production Pipeline
Run the complete 7-stage pipeline (triage, extract, reconcile, write, verify, critic):
```bash
research-agent run --ticker SRVCABLE --pack data/research_pack --as-of 2026-09-23 --variant full
```
Outputs are written to `out/briefs/SRVCABLE_brief.md` and `out/traces/SRVCABLE_<timestamp>.json`.

### Pipeline Variants for Evaluation
```bash
# Baseline variant: single raw prompt without triage or fact extraction
research-agent run --ticker SRVCABLE --pack data/research_pack --variant baseline

# Triage variant: triage and quote extraction without reconciliation
research-agent run --ticker SRVCABLE --pack data/research_pack --variant triage
```

---

## 3. How It Works

```
research_pack/*.md
      |
      v
[1 Ingest]            parse front matter, body, assign stable IDs (S1..Sn), age vs as-of date
      |
      v
[2 Sanitise + scan]   strip HTML comments, scan for injection phrases, record findings
      |
      v
[3 Triage]   (LLM)    per document: entity match, source class, reliability, staleness, usability
      |
      v
[4 Extract]  (LLM)    atomic facts with supporting quotes; verified in code as substrings
      |
      v
[5 Reconcile] (code)  group by (metric, period), source priority rules, arithmetic checks
      |
      v
[6 Write]    (LLM)    draft brief from verified fact table only (writer never sees raw docs)
      |
      v
[7 Verify]   (code + LLM) citation check, forbidden phrases, structure, critic repair loop
      |
      v
out/briefs/<TICKER>_brief.md  +  out/traces/<TICKER>_<timestamp>.json
```

### Key Design Choices
1. **The Writer Never Sees Raw Documents:** Feeding the writer LLM only the structured, verified fact table and triage notes ensures hidden prompt injections inside scraped texts cannot hijack summary generation.
2. **Quote Verification as Code:** Every extracted atomic fact requires an exact quote that Python verifies as a case-insensitive substring in the source body, instantly dropping hallucinated claims.
3. **Deterministic Reconciliation:** Source priority is defined as a concrete numeric mapping in `config.py` rather than loose prompt guidelines, allowing conflicting numbers to be compared systematically.
4. **Arithmetic Cross-Checks:** Python verifies mathematical relationships (such as calculating that EBITDA ₹140 cr / Revenue ₹1,248 cr equals the reported 11.2% margin, while ₹1,428 cr yields 9.8%) to resolve data contradictions with evidence.
5. **Multi-Layered Post-Verification:** Code checks validate citation resolution, ensure every sentence in the core sections has a source tag, and prohibit promotional buzzwords before an LLM critic audits attribution.

---

## 4. Models Used and Rationale

- **Default Model:** `gemini-3.5-flash-lite` (via the official `google-genai` SDK; configurable via `GEMINI_MODEL` in `.env`)
- **Why Flash-Class:** Fast inference, robust structured JSON schema support, generous free-tier limits, and low latency across multi-step pipeline iterations.
- **Temperature Settings:**
  - `triage` (0.1) and `extract` (0.1): Minimal randomness for deterministic classification and exact quote matching.
  - `write` (0.3): Balanced tone for clear, fluent plain-English drafting.
  - `critic` (0.2): Restrained analytical evaluation for detecting unattributed assertions.

---

## 5. Repository Layout

```
sarvottam-research-agent/
├── README.md                 <- Project overview and guide
├── pyproject.toml            <- Packaging metadata and console script
├── requirements.txt          <- Minimal pinned dependencies
├── .env.example              <- Template for environment variables
├── .gitignore                <- Ignored build artifacts and keys
├── Makefile                  <- test, lint, run, scan shortcuts
├── prompts/
│   ├── system_prompt.md      <- Core system prompt (required standalone file)
│   ├── triage.md             <- Document triage prompt
│   ├── extract.md            <- Fact extraction prompt
│   ├── write_brief.md        <- Research brief writing prompt
│   └── critic.md             <- Verification critic prompt
├── src/research_agent/
│   ├── __init__.py
│   ├── cli.py                <- CLI interface with run and scan commands
│   ├── config.py             <- Source priorities, constants, and patterns
│   ├── models.py             <- Pydantic models for pipeline data
│   ├── ingest.py             <- Front matter parser and loader
│   ├── sanitize.py           <- Comment stripper and injection scanner
│   ├── llm.py                <- Gemini API client with retries
│   ├── triage.py             <- Document classifier and entity checker
│   ├── extract.py            <- Atomic fact extractor and quote matcher
│   ├── reconcile.py          <- Conflict resolver and arithmetic checker
│   ├── write.py              <- Brief generator (fact table grounded)
│   ├── verify.py             <- Citations, rules, and critic verifier
│   └── pipeline.py           <- Pipeline orchestrator
├── data/
│   └── research_pack/        <- 8 scraped documents for SRVCABLE
├── tests/
│   ├── test_ingest.py        <- Tests for parser and file loading
│   ├── test_sanitize.py      <- Tests for injection detection & cleaning
│   ├── test_reconcile.py     <- Tests for conflict priority and math
│   └── test_verify.py        <- Tests for citation and phrase checks
├── runs/
│   ├── run_1_baseline/       <- Baseline outputs, trace, and prompts
│   ├── run_2_triage/         <- Triage outputs, trace, and prompts
│   └── run_3_verify/         <- Final run outputs, trace, and prompts
├── out/
│   ├── briefs/               <- Generated research briefs
│   └── traces/               <- Structured execution traces
├── docs/
│   ├── DECISIONS.md          <- Architectural decisions and trade-offs
│   ├── TEST_LOG.md           <- Detailed test logs across 3 runs
│   ├── RECORDING_SCRIPT.md   <- Timed script for the screen recording
│   └── SUBMISSION.md         <- Ready-to-paste submission form text
└── scripts/
    └── run_all.sh            <- Shell runner for all three variants
```

---

## 6. Known Limitations

1. **Unverifiable Management Assertions:** The agent can accurately identify and attribute management claims ("management says"), but cannot independently verify whether management will successfully pass through raw material costs or achieve growth forecasts.
2. **Quote Normalisation Boundaries:** Substring quote matching catches outright fabrications, but subtle transcription discrepancies (such as smart quotes or minor OCR misspellings) can cause genuine quotes to be dropped.
3. **Absence of Live Market Data:** The current pack contains only historical snapshots. Without real-time NSE price feeds, valuation multiples (P/E, EV/EBITDA) and current share prices cannot be determined.
4. **Single-Quarter Financial Scope:** Scraped filings provide Q1 FY27 figures, but lack comprehensive full-year cash flow statements and detailed debt maturity schedules.
5. **Static Priority Heuristics:** The source priority hierarchy assumes exchange filings trump news articles. In edge cases where an exchange disclosure contains an amended typo subsequently corrected by a press note, human intervention remains necessary.
6. **Locale & Formatting:** The system is tailored to Indian capital market standards (₹, crore, lakh) and English documents; adapting to other markets requires reconfiguring number parsers and prompts.

---

## 7. How to Extend: Adding a Live-Data Tool

To add real-time market data (such as live prices and valuation ratios):
1. Create a `src/research_agent/live.py` module using `yfinance` or an official NSE scraper.
2. Add a `--live` CLI flag in `cli.py` that queries public market data for real NSE tickers.
3. Wrap retrieved market quotes into a synthetic `SanitisedDocument` labeled with doc_type `live_market_data`.
4. Feed the live market document through the standard `extract.py` and `reconcile.py` stages so the writer can report current valuations while maintaining strict source traceability.

---

## 8. Running Tests and Linters

```bash
# Run pytest test suite (28 tests)
make test
# Or: python -m pytest tests/ -v

# Run ruff code linter and formatting checks
make lint
# Or: python -m ruff check src/ tests/ && python -m ruff format --check src/ tests/
```
