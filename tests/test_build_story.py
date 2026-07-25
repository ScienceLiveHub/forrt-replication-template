"""Tests for scripts/build_story.py — the reader-facing story-page generator.

The generator is deterministic: it turns a published FORRT chain (or research
synthesis) into a self-contained HTML article, every value read from the signed
nanopublications. A live build needs the network and SCIENCELIVE_API_KEY, so
these tests exercise only the offline, pure parts: the prose/label helpers, the
CSS asset loader, and the PUBLISHED.md apex selection. They also guard the one
thing that would break `pixi run -e tests test` — importing the module must not
require the API key.

Run: pixi run -e tests test
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_story as bs  # noqa: E402


def test_module_imports_without_api_key(monkeypatch):
    """Importing the module (done above) must not need the key — otherwise the
    whole test env fails to collect. The key is only read when a build runs."""
    monkeypatch.delenv("SCIENCELIVE_API_KEY", raising=False)
    with pytest.raises(SystemExit):
        bs._api_key()


def test_first_sentence_guards_abbreviations():
    text = ("Sent et al. (2021) reported that Sentinel-2 retrieves parameters with "
            "parameter-dependent accuracy. A second sentence follows.")
    # must not split at "et al." — the first real sentence ends at the first period
    assert bs.first_sentence(text) == (
        "Sent et al. (2021) reported that Sentinel-2 retrieves parameters with "
        "parameter-dependent accuracy.")


def test_first_sentence_collapses_whitespace():
    # newlines (hard-wrapped nanopub prose) collapse to single spaces; the
    # first real sentence (>= the 40-char floor) is returned, not the whole text
    assert bs.first_sentence("A finding that wraps\n   onto the next line here. Second one.") == \
        "A finding that wraps onto the next line here."


def test_first_list_item_numbered_and_bulleted():
    numbered = "1. Do not treat it as one thing.\n2. Validate per parameter."
    assert bs.first_list_item(numbered) == "Do not treat it as one thing."
    bulleted = "- first point\n- second point"
    assert bs.first_list_item(bulleted) == "first point"
    # no list -> falls back to the first sentence
    assert bs.first_list_item("Just prose here, no list at all.") == \
        "Just prose here, no list at all."


def test_prose_blocks_bullets_with_intro_and_continuations():
    text = ("This synthesis holds within the following scope:\n\n"
            "- Domain: a turbid estuary\n  (the Westerschelde).\n"
            "- Processing chain: fully open-source Acolite.")
    html = bs.prose_blocks(text)
    assert "<p>This synthesis holds within the following scope:</p>" in html
    assert html.count("<li>") == 2
    # the indented continuation line joins its item, not a new one
    assert "a turbid estuary (the Westerschelde)." in html
    assert "<ul" in html


def test_prose_blocks_numbered_becomes_ol():
    text = "1. First recommendation here.\n2. Second recommendation here."
    html = bs.prose_blocks(text)
    assert "<ol" in html and html.count("<li>") == 2


def test_prose_blocks_plain_paragraphs():
    html = bs.prose_blocks("Para one.\n\nPara two.")
    assert html.count("<p>") == 2 and "<ul" not in html and "<ol" not in html


def test_raw_to_blob():
    raw = "https://raw.githubusercontent.com/annefou/sado-estuary/main/figures/study_area.png"
    assert bs.raw_to_blob(raw) == \
        "https://github.com/annefou/sado-estuary/blob/main/figures/study_area.png"
    # anything that is not a raw URL is returned unchanged
    other = "https://doi.org/10.3390/rs13051043"
    assert bs.raw_to_blob(other) == other


def test_verdict_class_mapping():
    assert bs.VERDICT_CLASS["validated"] == "ok"
    assert bs.VERDICT_CLASS["partiallysupported"] == "warn"
    assert bs.VERDICT_CLASS["contradicted"] == "bad"


def test_load_style_reads_committed_asset():
    style = bs.load_style()
    assert style.startswith("<style>") and style.rstrip().endswith("</style>")
    # the Science Live palette must be present (self-contained, matches the platform)
    assert "--brand:#be2e78" in style          # Science Live magenta
    assert "@font-face" in style               # display font embedded


def test_apex_from_published_prefers_synthesis(tmp_path):
    """The apex is the Research Synthesis (08) when published, else the Outcome (05)."""
    nano = tmp_path / "nanopubs"
    nano.mkdir()
    syn = "https://w3id.org/sciencelive/np/RA" + "S" * 30
    out = "https://w3id.org/sciencelive/np/RA" + "O" * 30
    table = (
        "| Step | Template | URI | Published |\n|---|---|---|---|\n"
        f"| 05 | Outcome | {out} | 2026 |\n"
        f"| 08 | Research Synthesis | {syn} | 2026 |\n")
    (nano / "PUBLISHED.md").write_text(table)
    assert bs.apex_from_published(tmp_path) == syn


def test_apex_from_published_falls_back_to_outcome(tmp_path):
    nano = tmp_path / "nanopubs"
    nano.mkdir()
    out = "https://w3id.org/sciencelive/np/RA" + "O" * 30
    table = (
        "| Step | Template | URI | Published |\n|---|---|---|---|\n"
        f"| 05 | Outcome | {out} | 2026 |\n"
        "| 08 | Research Synthesis | _not yet published_ | |\n")
    (nano / "PUBLISHED.md").write_text(table)
    assert bs.apex_from_published(tmp_path) == out


def test_apex_from_published_none_when_missing(tmp_path):
    assert bs.apex_from_published(tmp_path) is None
