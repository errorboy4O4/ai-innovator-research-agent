"""Parse research-pack markdown files into Document objects."""

from __future__ import annotations

import logging
import re
from datetime import date, datetime
from pathlib import Path

from .models import Document

logger = logging.getLogger(__name__)


def parse_front_matter(text: str) -> dict[str, str]:
    """Extract YAML-like front matter between --- delimiters."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        raise ValueError("Missing front matter (expected --- delimiters)")

    fields: dict[str, str] = {}
    for line in match.group(1).strip().splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        fields[key.strip()] = val.strip()
    return fields


def parse_date(date_str: str) -> date:
    """Parse a date string in YYYY-MM-DD format."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as e:
        raise ValueError(f"Cannot parse date '{date_str}': {e}") from e


def extract_body(text: str) -> str:
    """Return everything after the closing --- of front matter."""
    match = re.match(r"^---\s*\n.*?\n---\s*\n", text, re.DOTALL)
    if not match:
        return text
    return text[match.end() :].strip()


def load_document(filepath: Path, doc_id: str, as_of: date) -> Document:
    """Load a single markdown file into a Document."""
    text = filepath.read_text(encoding="utf-8")
    front = parse_front_matter(text)

    required = ["source", "published", "type"]
    for key in required:
        if key not in front:
            raise ValueError(f"{filepath.name}: missing front-matter field '{key}'")

    pub_date = parse_date(front["published"])
    age_days = (as_of - pub_date).days

    return Document(
        id=doc_id,
        filename=filepath.name,
        source=front.get("source", ""),
        url=front.get("url", ""),
        published=pub_date,
        doc_type=front.get("type", ""),
        body=extract_body(text),
        age_days=age_days,
    )


def load_research_pack(pack_dir: Path, as_of: date) -> list[Document]:
    """Load all .md files from a directory, sorted by filename for stable IDs."""
    md_files = sorted(pack_dir.glob("*.md"))
    if not md_files:
        raise FileNotFoundError(f"No .md files found in {pack_dir}")

    docs = []
    for i, filepath in enumerate(md_files, start=1):
        doc_id = f"S{i}"
        try:
            doc = load_document(filepath, doc_id, as_of)
            logger.info(
                "Loaded %s: %s (%s, age %d days)", doc_id, filepath.name, doc.doc_type, doc.age_days
            )
            docs.append(doc)
        except ValueError as e:
            logger.error("Failed to load %s: %s", filepath.name, e)
            raise

    return docs
