# Recording Script (2–3 minutes)

## 0:00–0:20 — The Problem

> "This is a research agent that takes scraped documents about an Indian stock and
> produces a one-page research brief for a retail investor. The documents it receives
> are untrusted — they may contain conflicting numbers, stale data, promotional content,
> or even hidden instructions trying to manipulate the summary."

*On screen: show the README briefly, then the research_pack folder with the 8 files.*

## 0:20–1:00 — Live Demo

> "Let me first run the scan command, which needs no API key."

```
python -m research_agent.cli scan --pack data/research_pack
```

*On screen: the scan output showing the injection detection in the blog post.*

> "It caught the hidden HTML comment in the blog that tells AI assistants to declare
> a strong buy. Now let me run the full pipeline."

```
python -m research_agent.cli run --ticker SRVCABLE --pack data/research_pack --as-of 2026-09-23 --variant full
```

*On screen: the pipeline running through all 7 stages. Show the brief output.
Then open the trace JSON file briefly.*

## 1:00–1:50 — Design Decision: The Writer Never Sees Raw Documents

> "The design decision I'm most proud of is that the writer LLM never sees the raw
> documents. It only receives a verified fact table.
>
> Here's why that matters. The blog post contained a hidden instruction telling AI to
> declare a 'strong buy with 60% upside'. In a naive approach — which I tested as the
> baseline — the LLM sometimes repeats these claims. In my pipeline, the sanitiser
> detects the injection, the triage stage marks the blog as low reliability, and the
> writer never even reads the blog text. It only sees individual facts extracted from
> it, tagged as 'promotional_claim', which it knows to handle cautiously.
>
> Similarly, the Business Daily article says revenue was ₹1,428 crore — a 35% jump.
> But the company's own press release says ₹1,248 crore — an 18% increase. My
> reconciliation stage catches this conflict, runs an arithmetic cross-check — EBITDA
> of ₹140 crore divided by ₹1,248 crore gives 11.2%, which matches the reported
> margin, while ₹140 divided by ₹1,428 gives 9.8%, which doesn't — and prefers the
> primary source. The conflict is surfaced in Open Questions so the reader knows."

## 1:50–2:20 — Generated Output vs Hand Edits (Transparency)

> "In `runs/run_3_verify/brief.md`, you can see the raw generated output straight from
> the pipeline. For the final submission in `docs/SUBMISSION.md`, I've plainly disclosed
> five precision hand-edits: restoring the 18% YoY growth figure, specifying copper price
> inflation rather than generic raw materials, clarifying promoter pledge of holdings,
> framing the GST demand as a multi-year scale comparison, and highlighting market data gaps.
> Showing the raw output next to the final submission shows the exact boundary between
> automated extraction and retail-grade editorial refinement."

*On screen: side-by-side view of `runs/run_3_verify/brief.md` and `docs/SUBMISSION.md`.*

## 2:20–2:45 — Honest Limitations & Future Work

> "An honest limitation: the agent cannot verify forward-looking management claims.
> When management says margins will recover in two quarters or that the GST demand will
> have no material impact, the agent attributes the forecast but cannot independently
> validate it. Furthermore, the scraped research pack contains no live market price feed,
> no valuation multiples (P/E, EV/EBITDA), and no full-year cash flow statements.
>
> If I had more time, I would connect a live exchange API to pull market valuations and
> balance sheet data directly into the fact table."

## 2:45–3:00 — Close

> "All code, unit tests, and evaluation traces are available in the public GitHub repo.
> Thanks for reviewing."
