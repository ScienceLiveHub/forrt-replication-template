"""Tests for scripts/build_chain_draft.py — the chain-draft.json producer.

The generator is a deterministic, offline script (the point is to keep the
publish phase off Claude tokens). These tests build a small fixture repo — a
CITATION.cff, PUBLISHED.md and a couple of filled drafts, plus the repo's real
committed template snapshot — and assert the produced chain-draft.json matches
the contract (docs/chain-draft-contract.md): correct field routing
(carry / metadata / manual / content), DOI forms, token omission, provenance,
and resume.

Run: pixi run -e tests test
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_chain_draft as bcd  # noqa: E402

TEMPLATES = ROOT / "nanopubs" / "templates"

CITATION = """\
cff-version: 1.2.0
title: "bombus-thermal-replication"
type: software
repository-code: "https://github.com/annefou/bombus-thermal-replication"
date-released: "2026-06-26"
identifiers:
  - type: doi
    value: "10.5281/zenodo.20943700"
    description: "Concept DOI (resolves to the latest version) — cite the project"
  - type: doi
    value: "10.5281/zenodo.20943752"
    description: "Version DOI for v0.1.0 — pins this exact release; cite this from nanopubs"
references:
  - type: article
    title: "Climate change contributes to widespread declines among bumble bees"
    doi: "10.1126/science.aax8591"
"""

PUBLISHED = """\
| Step | Template | URI | Published |
|---|---|---|---|
| 01 | Quote | https://w3id.org/sciencelive/np/RAquoteExample0000000000000000000000000000 | 2026-06-27 |
| 02 | AIDA | _not yet published_ | |
"""

QUOTE = """\
# 01 — Quote
### DOI of the paper (starting with '10.')
```
10.1126/science.aax8591
```
### The exact quotation from the paper (max. 500 characters)
```
Bumblebee species are declining where temperatures exceed historical limits.
```
### our interpretation and explanation of why this quotation is relevant (max. 800 characters)
```
We test whether this holds for Iberian Bombus on an equal-area HEALPix grid.
```
"""

OUTCOME = """\
# 05 — Outcome
### short URI suffix for outcome ID
```
iberian-bombus-outcome
```
### plain-text label for the outcome
```
Iberian Bombus thermal-exposure outcome
```
### choose study
```
```
### repository URL
```
{{ZENODO_VERSION_DOI}}
```
### choose completion date
```
{{RELEASE_DATE}}
```
### choose validation status
- [ ] validated
### describe the overall conclusion about the original claim
```
The thermal-exposure signal holds on the equal-area grid.
```
### describe the evidence that supports your conclusion
```
GLMM coefficient +0.454 (95% HDI [+0.130, +0.751]).
```
### choose confidence level
### describe what limits the conclusions of the study
```
Single taxon and region.
```
"""


def _fixture_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "nanopubs" / "drafts").mkdir(parents=True)
    # real committed template snapshot + registry
    import shutil
    shutil.copytree(TEMPLATES, root / "nanopubs" / "templates")
    (root / "CITATION.cff").write_text(CITATION)
    (root / "nanopubs" / "PUBLISHED.md").write_text(PUBLISHED)
    (root / "nanopubs" / "drafts" / "01_quote.md").write_text(QUOTE)
    (root / "nanopubs" / "drafts" / "05_outcome.md").write_text(OUTCOME)
    for s in ("02_aida", "03_claim", "04_study", "06_citation"):
        (root / "nanopubs" / "drafts" / f"{s}.md").write_text(f"# {s}\n")
    return root


@pytest.fixture
def draft(tmp_path):
    root = _fixture_repo(tmp_path)
    return bcd.build_chain_draft(root, repository="https://github.com/annefou/bombus-thermal-replication",
                                 commit="abc123")


def _step(draft, sid):
    return next(s for s in draft["steps"] if s["step"] == sid)


# --- shape / structure ---------------------------------------------------

def test_shape_and_backbone(draft):
    assert draft["schema_version"] == bcd.SCHEMA_VERSION
    assert draft["chain_shape"] == "paper-rooted"
    assert [s["step"] for s in draft["steps"]] == \
        ["01_quote", "02_aida", "03_claim", "04_study", "05_outcome", "06_citation"]


def test_carry_forward_edges_match_the_contract(draft):
    assert draft["carry_forward"] == [
        {"from": "01_quote", "into": "02_aida", "field": "project"},
        {"from": "02_aida", "into": "03_claim", "field": "aida"},
        {"from": "03_claim", "into": "04_study", "field": "claim"},
        {"from": "04_study", "into": "05_outcome", "field": "study"},
        {"from": "05_outcome", "into": "06_citation", "field": "work"},
    ]


# --- metadata routing (CITATION.cff), in the right DOI form --------------

def test_paper_doi_is_bare_on_quote_full_url_elsewhere(draft):
    assert _step(draft, "01_quote")["prefill"]["paper"] == "10.1126/science.aax8591"
    assert _step(draft, "03_claim")["prefill"]["source"] == "https://doi.org/10.1126/science.aax8591"
    assert _step(draft, "06_citation")["prefill"]["cited"] == "https://doi.org/10.1126/science.aax8591"


def test_outcome_uses_version_doi_and_release_date(draft):
    out = _step(draft, "05_outcome")["prefill"]
    assert out["repo"] == "https://doi.org/10.5281/zenodo.20943752"   # version, not concept DOI
    assert out["date"] == "2026-06-26"


def test_placeholder_tokens_in_draft_fences_are_never_emitted(draft):
    # 05_outcome.md had {{ZENODO_VERSION_DOI}}/{{RELEASE_DATE}} in its fences.
    for s in draft["steps"]:
        for v in s["prefill"].values():
            assert "{{" not in v


# --- content routing (drafts) --------------------------------------------

def test_drafted_content_is_extracted(draft):
    q = _step(draft, "01_quote")["prefill"]
    assert q["quotation"].startswith("Bumblebee species are declining")
    assert q["comment"].startswith("We test whether")
    out = _step(draft, "05_outcome")["prefill"]
    assert out["outcome"] == "iberian-bombus-outcome"          # id slug
    assert out["label"] == "Iberian Bombus thermal-exposure outcome"
    assert out["conclusion"].startswith("The thermal-exposure signal")
    assert out["evidence"].startswith("GLMM coefficient")
    assert out["limitations"] == "Single taxon and region."


def test_provenance_is_recorded(draft):
    prov = _step(draft, "05_outcome")["provenance"]
    assert prov["repo"] == "CITATION.cff"
    assert prov["conclusion"] == "nanopubs/drafts/05_outcome.md"


# --- manual + carry: not pre-filled --------------------------------------

def test_restricted_choice_fields_are_manual_not_prefilled(draft):
    out = _step(draft, "05_outcome")
    assert set(out["manual"]) == {"validationStatus", "confidenceLevel"}
    assert "validationStatus" not in out["prefill"]
    assert _step(draft, "03_claim")["manual"] == ["forrtType"]
    assert _step(draft, "06_citation")["manual"] == ["cites"]


def test_carry_fields_are_absent_from_prefill(draft):
    assert "study" not in _step(draft, "05_outcome")["prefill"]     # carried from 04
    assert "work" not in _step(draft, "06_citation")["prefill"]     # carried from 05
    assert "aida" not in _step(draft, "03_claim")["prefill"]        # carried from 02


# --- resume (PUBLISHED.md) -----------------------------------------------

def test_published_uri_is_read_for_resume(draft):
    assert _step(draft, "01_quote")["published_uri"].endswith("RAquoteExample0000000000000000000000000000")
    assert _step(draft, "02_aida")["published_uri"] is None


# --- unit helpers --------------------------------------------------------

def test_load_citation_ignores_placeholder_tokens():
    cff = bcd.load_citation('title: x\nrepository-code: "https://github.com/{{REPO_ORG}}/{{REPO_NAME}}"\n'
                            'date-released: "{{RELEASE_DATE}}"\n')
    assert cff.get("repo_url") is None and cff.get("date_released") is None


def test_bare_doi_strips_resolver_prefix():
    assert bcd._bare_doi("https://doi.org/10.1/x") == "10.1/x"
    assert bcd._bare_doi("10.1/x") == "10.1/x"


def test_parse_published_skips_unpublished_rows():
    pub = bcd.parse_published(PUBLISHED)
    assert "01" in pub and "02" not in pub


def test_uninitialised_template_yields_empty_prefill():
    """Run against the repo's own uninitialised drafts: every value is a token or
    empty, so nothing is pre-filled, but the structure and manual lists stand."""
    d = bcd.build_chain_draft(ROOT, repository="x", commit="y")
    assert all(s["prefill"] == {} for s in d["steps"])
    assert _step(d, "05_outcome")["manual"] == ["validationStatus", "confidenceLevel"]
