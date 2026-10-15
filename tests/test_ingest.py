"""Tests for the ingest module: front-matter parsing and document loading."""

from datetime import date

import pytest

from research_agent.ingest import extract_body, load_document, parse_date, parse_front_matter

SAMPLE_DOC = """---
source: Test Corp investor relations
url: https://example.com/test
published: 2026-08-08
type: official company filing
---

# Test Corp announces results

Revenue was ₹500 crore.
"""


def test_parse_front_matter():
    fields = parse_front_matter(SAMPLE_DOC)
    assert fields["source"] == "Test Corp investor relations"
    assert fields["published"] == "2026-08-08"
    assert fields["type"] == "official company filing"
    assert fields["url"] == "https://example.com/test"


def test_parse_front_matter_missing():
    with pytest.raises(ValueError, match="Missing front matter"):
        parse_front_matter("No front matter here.")


def test_parse_date_valid():
    d = parse_date("2026-08-08")
    assert d == date(2026, 8, 8)


def test_parse_date_invalid():
    with pytest.raises(ValueError, match="Cannot parse date"):
        parse_date("not-a-date")


def test_extract_body():
    body = extract_body(SAMPLE_DOC)
    assert body.startswith("# Test Corp announces results")
    assert "Revenue was ₹500 crore." in body
    assert "---" not in body
    assert "source:" not in body


def test_load_document(tmp_path):
    doc_file = tmp_path / "test_doc.md"
    doc_file.write_text(SAMPLE_DOC, encoding="utf-8")

    doc = load_document(doc_file, "S1", date(2026, 9, 23))
    assert doc.id == "S1"
    assert doc.source == "Test Corp investor relations"
    assert doc.published == date(2026, 8, 8)
    assert doc.age_days == 46
    assert "Revenue was ₹500 crore." in doc.body


def test_load_document_missing_field(tmp_path):
    bad_doc = """---
source: Test
url: https://example.com
---

Content without a published date.
"""
    doc_file = tmp_path / "bad.md"
    doc_file.write_text(bad_doc, encoding="utf-8")

    with pytest.raises(ValueError, match="missing front-matter field 'published'"):
        load_document(doc_file, "S1", date(2026, 9, 23))
