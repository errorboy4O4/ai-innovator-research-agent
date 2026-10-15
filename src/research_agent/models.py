from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class Document(BaseModel):
    """A parsed research-pack document with front matter and body."""

    id: str
    filename: str
    source: str
    url: str
    published: date
    doc_type: str
    body: str
    age_days: int = 0


class FindingKind(str, Enum):
    HTML_COMMENT = "html_comment"
    INJECTION_PHRASE = "injection_phrase"
    ZERO_WIDTH_CHAR = "zero_width_char"


class Finding(BaseModel):
    doc_id: str
    kind: FindingKind
    excerpt: str
    location: str


class SanitisedDocument(BaseModel):
    """Document after sanitisation, with cleaned body and findings."""

    id: str
    filename: str
    source: str
    url: str
    published: date
    doc_type: str
    body: str
    original_body: str
    age_days: int = 0
    findings: list[Finding] = Field(default_factory=list)
    has_injection: bool = False


class Reliability(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Usability(str, Enum):
    FULL = "full"
    LIMITED = "limited"
    EXCLUDED = "excluded"


class SourceClass(str, Enum):
    OFFICIAL_FILING = "official_filing"
    OFFICIAL_TRANSCRIPT = "official_transcript"
    NEWS = "news"
    BLOG = "blog"
    PROMOTIONAL = "promotional"


class TriageResult(BaseModel):
    doc_id: str
    entity_match: bool
    entity_note: str
    source_class: SourceClass
    reliability: Reliability
    is_stale: bool
    usable: Usability
    reason: str


class FactType(str, Enum):
    REPORTED_FIGURE = "reported_figure"
    MANAGEMENT_CLAIM = "management_claim"
    THIRD_PARTY_REPORT = "third_party_report"
    PROMOTIONAL_CLAIM = "promotional_claim"
    OWN_CALCULATION = "own_calculation"


class ExtractedFact(BaseModel):
    fact_id: str
    source_id: str
    metric: str
    value: str
    unit: str = ""
    period: str = ""
    fact_type: FactType
    statement: str
    quote: str


class ConflictRecord(BaseModel):
    metric: str
    period: str
    facts: list[ExtractedFact]
    preferred_fact_id: str
    resolution: str


class VerifiedFact(BaseModel):
    """A fact that passed reconciliation, with preference metadata."""

    fact: ExtractedFact
    preferred: bool = False
    superseded_by: str | None = None
    is_historical: bool = False


class PipelineTrace(BaseModel):
    """Full trace of a pipeline run for reproducibility."""

    ticker: str
    as_of: str
    model: str
    variant: str
    timestamp: str
    documents_loaded: int = 0
    findings: list[Finding] = Field(default_factory=list)
    triage_results: list[TriageResult] = Field(default_factory=list)
    facts_extracted: int = 0
    facts_dropped: int = 0
    conflicts: list[ConflictRecord] = Field(default_factory=list)
    verification_passed: bool = False
    verification_issues: list[str] = Field(default_factory=list)
    repair_attempts: int = 0
    brief_word_count: int = 0
