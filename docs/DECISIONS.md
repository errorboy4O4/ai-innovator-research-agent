# Design Decisions

## 1. No agent framework (LangChain, LangGraph, CrewAI)

**Alternatives considered:** LangChain with LCEL, LangGraph, CrewAI.

**Reason:** A plain Python pipeline is easier to explain, debug, and trust. Each stage
is a simple function call. The evaluators can read the code top-to-bottom without
needing to understand a framework's abstractions. The pipeline has only 7 stages with
deterministic flow — no routing, branching, or agent loops that would justify a framework.

## 2. Writer never sees raw documents

**Alternatives considered:** Passing all documents to the writer, passing summaries.

**Reason:** The writer receives only the verified fact table, triage metadata, and
conflict records. This is the primary defence against prompt injection: even if a
document contains hidden instructions, the writer never reads them. It also forces
the writer to ground every claim in a verified fact rather than hallucinating from
raw text.

## 3. Quotes must be exact substrings

**Alternatives considered:** Fuzzy matching, semantic similarity.

**Reason:** Requiring the LLM's extracted quote to appear as an exact substring
(whitespace-normalised) in the source document catches hallucinated facts at extract
time. If the LLM paraphrases or invents a quote, the fact is dropped and logged.
This is a simple, deterministic check that adds real safety.

## 4. Source priority encoded as data, not prose

**Alternatives considered:** Describing priority rules only in the prompt.

**Reason:** The priority table in `config.py` is a dictionary mapping source class
to numeric rank. This makes the reconciliation logic testable in plain Python without
an LLM. The prompt also describes the rule so the LLM understands it, but the code
enforces it.

## 5. Separate system prompt file

**Alternatives considered:** Embedding the prompt in Python code.

**Reason:** The assignment requires the system prompt as a separate file that
reviewers will read first. Keeping all prompts in `prompts/` also makes them
easy to version, compare between runs, and iterate on independently of the code.

## 6. Temperature choices

**Alternatives considered:** Default temperature for all calls.

**Reason:** Low temperature (0.1) for triage and extraction, where we want
deterministic, factual output. Slightly higher (0.3) for the writer, where
some fluency variation is acceptable. The critic uses 0.2 to balance
thoroughness with consistency.

## 7. Attribution of management claims

**Alternatives considered:** Treating all sources equally.

**Reason:** Management statements are inherently self-serving. Guidance, forecasts,
and qualitative claims must be attributed ("management says") so the reader can
judge their reliability. This is enforced both in the system prompt and checked
by the critic.

## 8. Treatment of stale sources

**Alternatives considered:** Ignoring publication date entirely.

**Reason:** For current-state metrics (ownership, pledge, price), a source
older than 12 months is stale. Stale data is marked `historical` and never
preferred over a newer fact. This prevents misleading the reader with outdated
figures while still allowing historical context.

## 9. Treatment of wrong-entity documents

**Alternatives considered:** Including them with a caveat.

**Reason:** A document about "Sarvottam Cable Network" (a cable TV operator) is
not about "Sarvottam Cables Ltd" (a cable manufacturer). Including wrong-entity
data, even with a caveat, risks contaminating the brief. We exclude it entirely
and state the reason in the Sources table.
