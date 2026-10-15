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

## 1:50–2:30 — Honest Limitation

> "An honest limitation: the agent cannot verify management claims. When the MD says
> margins will recover in two quarters, or that the GST demand won't have a material
> impact, the agent can only attribute the claim — it can't check it. It also has no
> live price data, no valuation multiples, and no peer comparison. And the LLM triage
> can sometimes misclassify unusual sources — the code overrides help, but they're not
> perfect.
>
> If I had more time, I'd add a live data stage that fetches current prices and basic
> valuation ratios from NSE, running them through the same sanitise-triage-extract
> pipeline."

## 2:30–2:45 — Close

> "The code is in the GitHub repo linked in my submission. Thanks for reviewing."
