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
- [x] contradicted
- [ ] inconclusive
### describe the overall conclusion about the original claim
```
The thermal-exposure signal holds on the equal-area grid.
```
### describe the evidence that supports your conclusion
```
GLMM coefficient +0.454 (95% HDI [+0.130, +0.751]).
```
### choose confidence level
- [x] high
- [ ] low
### describe what limits the conclusions of the study
```
Single taxon and region.
```
"""

CLAIM = """\
# 03 — Claim
### label of the claim, to find it later
```
Thermal exposure predicts Iberian Bombus extirpation
```
### Type of FORRT claim
- [ ] statistical significance
- [x] descriptive pattern
- [ ] model performance
"""

STUDY = """\
# 04 — Study
### label/name of replication study
```
Iberian Bombus thermal-exposure replication
```
### choose the study type
- [ ] Reproduction Study
- [x] Replication Study
### choose terms as related keywords
- _Label 1: thermal ecology
- _Label 2: bumblebee
### Choose the scientific discipline
- _Discipline label: ecology
"""


SOFTWARE = """\
# 07 — Research Software
### title of published software
```
Iberian Bombus thermal-exposure replication code
```
"""

SYNTHESIS = """\
# 08 — Research Synthesis
### label
```
Thermal exposure and Bombus extirpation - synthesis
```
### Conclusion of the synthesis
```
Increased thermal exposure predicts higher extirpation across regions.
```
"""


# Offline stand-in for the live Wikidata lookup.
def _mock_wikidata(label: str):
    return {"uri": "http://www.wikidata.org/entity/Q" + str(abs(hash(label)) % 1000),
            "label": label}


def _fixture_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "nanopubs" / "drafts").mkdir(parents=True)
    # real committed template snapshot + registry
    import shutil
    shutil.copytree(TEMPLATES, root / "nanopubs" / "templates")
    (root / "CITATION.cff").write_text(CITATION)
    (root / "nanopubs" / "PUBLISHED.md").write_text(PUBLISHED)
    (root / "nanopubs" / "drafts" / "01_quote.md").write_text(QUOTE)
    (root / "nanopubs" / "drafts" / "03_claim.md").write_text(CLAIM)
    (root / "nanopubs" / "drafts" / "04_study.md").write_text(STUDY)
    (root / "nanopubs" / "drafts" / "05_outcome.md").write_text(OUTCOME)
    for s in ("02_aida", "06_citation"):
        (root / "nanopubs" / "drafts" / f"{s}.md").write_text(f"# {s}\n")
    return root


@pytest.fixture
def draft(tmp_path):
    root = _fixture_repo(tmp_path)
    return bcd.build_chain_draft(root, repository="https://github.com/annefou/bombus-thermal-replication",
                                 commit="abc123", resolve_wikidata=_mock_wikidata)


@pytest.fixture
def draft_full(tmp_path):
    """Fixture repo that ALSO drafts the two optional side-branches (07/08)."""
    root = _fixture_repo(tmp_path)
    d = root / "nanopubs" / "drafts"
    d.joinpath("07_research_software.md").write_text(SOFTWARE)
    d.joinpath("08_synthesis.md").write_text(SYNTHESIS)
    return bcd.build_chain_draft(root, repository="https://github.com/annefou/bombus-thermal-replication",
                                 commit="abc123", resolve_wikidata=_mock_wikidata)


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
    # 06_citation's DOI lives in the st02 repeatable row, not a flat key (below).


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


# --- judgment fields: the agent's recorded choice, pre-filled + flagged --

def test_judgment_fields_prefilled_from_draft_choice_and_flagged(draft):
    """The agent ticked one option per judgment field in the draft; that choice
    is pre-filled (overriding the form default) AND kept in `manual` so the wizard
    shows 'confirm', not left blank."""
    out = _step(draft, "05_outcome")
    assert out["prefill"]["validationStatus"].endswith("Contradicted")
    assert out["prefill"]["confidenceLevel"].endswith("HighConfidence")
    assert set(out["manual"]) == {"validationStatus", "confidenceLevel"}
    claim = _step(draft, "03_claim")
    assert claim["prefill"]["forrtType"].endswith("descriptive_pattern-FORRT-Claim")
    assert claim["manual"] == ["forrtType"]
    assert _step(draft, "04_study")["prefill"]["type"].endswith("Replication-Study")


# --- repeatable CiTO citation --------------------------------------------

def test_citation_is_a_prepared_st02_row(draft):
    """CiTO is the repeatable `st02` array, not flat cites/cited; one row is
    prepared with the relation derived from the validation status."""
    cite = _step(draft, "06_citation")["prefill"]
    assert "cited" not in cite and "cites" not in cite      # not flat
    row = cite["st02"][0]
    assert row["cited"] == "https://doi.org/10.1126/science.aax8591"
    assert row["cites"] == "http://purl.org/spar/cito/disputes"   # Contradicted -> disputes
    assert _step(draft, "06_citation").get("manual", []) == []


# --- generated id slug ---------------------------------------------------

def test_id_slug_is_generated_from_org_repo_step(draft):
    """Steps whose draft has no URI-suffix slug get <org>-<repo>-<step>."""
    assert _step(draft, "03_claim")["prefill"]["claim"] == "annefou-bombus-thermal-replication-claim"
    assert _step(draft, "04_study")["prefill"]["study"] == "annefou-bombus-thermal-replication-study"


# --- Wikidata concept fields (resolved from draft labels) ----------------

def test_wikidata_fields_resolved_to_form_shapes(draft):
    """Keyword labels -> keywordSelection [{uri,label}]; discipline -> a single
    {uri,label} object (not an array), matching the components."""
    study = _step(draft, "04_study")["prefill"]
    assert [k["label"] for k in study["keywordSelection"]] == ["thermal ecology", "bumblebee"]
    assert all(k["uri"].startswith("http://www.wikidata.org/entity/Q") for k in study["keywordSelection"])
    assert study["disciplineSelection"]["label"] == "ecology"          # single object
    assert not isinstance(study["disciplineSelection"], list)


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


# --- optional side-branches (07 software, 08 synthesis) + their back-links ---

def test_optional_steps_appended_when_drafted(draft_full):
    # (the not-drafted -> absent case is covered by test_shape_and_backbone)
    assert [s["step"] for s in draft_full["steps"]] == \
        ["01_quote", "02_aida", "03_claim", "04_study", "05_outcome",
         "06_citation", "07_research_software", "08_synthesis"]


def test_back_link_carry_edges_are_emitted(draft_full):
    """07/08 link back to NON-ADJACENT steps, with several links and shaped
    targets. The linear 01->06 edges are unchanged; the back-links are added."""
    edges = draft_full["carry_forward"]
    # linear edges still present and unchanged
    assert {"from": "05_outcome", "into": "06_citation", "field": "work"} in edges
    # 07 <- Claim (scalar) + Outcome (array of strings)
    assert {"from": "03_claim", "into": "07_research_software", "field": "project"} in edges
    assert {"from": "05_outcome", "into": "07_research_software",
            "field": "researchOutputs", "mode": "uriList"} in edges
    # 08 <- Outcome (array of {source} objects)
    assert {"from": "05_outcome", "into": "08_synthesis", "field": "sources",
            "mode": "uriObjectList", "itemKey": "source"} in edges


def test_back_link_fields_are_absent_from_prefill(draft_full):
    """The carried back-links must not be content/metadata-filled here — the
    wizard injects them from the referenced steps' published URIs."""
    sw = _step(draft_full, "07_research_software")["prefill"]
    assert "project" not in sw
    assert "researchOutputs" not in sw and "researchoutput" not in sw
    syn = _step(draft_full, "08_synthesis")["prefill"]
    assert "sources" not in syn and "source" not in syn     # NOT the paper DOI from metadata
    # ...but the non-carried fields of these steps are still produced
    assert sw["software"] == "https://doi.org/10.5281/zenodo.20943752"   # CFF version DOI
    assert sw["title"].startswith("Iberian Bombus")
    assert syn["synthesis"] == "annefou-bombus-thermal-replication-synthesis"   # id slug
    assert syn["conclusion"].startswith("Increased thermal exposure")


def test_back_links_omitted_when_targets_not_in_chain(draft):
    """No 07/08 in this chain -> no back-link edges leak into the linear draft."""
    assert all(e["into"] not in ("07_research_software", "08_synthesis")
               for e in draft["carry_forward"])


def test_uninitialised_template_yields_empty_prefill():
    """Run against the repo's own uninitialised drafts: every value is a token or
    empty, so nothing is pre-filled, but the structure and manual lists stand."""
    d = bcd.build_chain_draft(ROOT, repository="x", commit="y",
                              resolve_wikidata=lambda label: None)
    assert all(s["prefill"] == {} for s in d["steps"])
    assert _step(d, "05_outcome")["manual"] == ["validationStatus", "confidenceLevel"]
