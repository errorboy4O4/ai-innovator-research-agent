from datetime import date
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"

DEFAULT_AS_OF = date(2026, 9, 23)

STALE_CUTOFF_DAYS = 365

# Source priority: lower number = higher authority.
# Ties within a tier: prefer the more recent document.
SOURCE_PRIORITY = {
    "official_filing": 1,
    "official_transcript": 2,
    "news": 3,
    "blog": 4,
    "promotional": 4,
    "unknown": 5,
}

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"note\s+for\s+ai",
    r"system\s+prompt",
    r"do\s+not\s+mention\s+this",
    r"you\s+must\s+state",
    r"as\s+an\s+ai\s+assistant",
]

FORBIDDEN_PHRASES = [
    "strong buy",
    "buy now",
    "target price",
    "price target",
    "analyst consensus",
    "multibagger",
    "guaranteed",
]

FACT_TYPES = [
    "reported_figure",
    "management_claim",
    "third_party_report",
    "promotional_claim",
    "own_calculation",
]

# Temperature settings per pipeline stage
TEMPERATURE = {
    "triage": 0.1,
    "extract": 0.1,
    "write": 0.3,
    "critic": 0.2,
}
