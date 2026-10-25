"""Tests for scripts/build_rocrate.py and the deposit plan of scripts/deposit_rohub.py.

Offline: the fixture repo is built in tmp_path from the shapes of a real replication
(annefou/natural-regeneration-replication: CITATION.cff after a release, PUBLISHED.md
with markdown-linked URIs), and DOI resolution is stubbed.

Run: pixi run -e tests test
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import build_rocrate  # noqa: E402
import deposit_rohub  # noqa: E402

NP = "https://w3id.org/sciencelive/np/RA"
CFF = """\
cff-version: 1.2.0
title: "demo-replication: testing a headline claim"
abstract: "Replication of a headline claim on new data."
authors:
  - given-names: Anne
    family-names: Fouilloux
    orcid: "https://orcid.org/0000-0002-1784-2920"
    affiliation: "LifeWatch ERIC"
license: MIT
version: 1.0.0
date-released: "2026-10-04"
doi: 10.5281/zenodo.100
repository-code: "https://github.com/example/demo-replication"
keywords: [replication, FORRT]
identifiers:
  - type: doi
    value: 10.5281/zenodo.102
    description: "Version DOI for v1.2.0"
  - type: swh
    value: "swh:1:rev:0123456789abcdef0123456789abcdef01234567"
references:
  - type: article
    title: "The original paper"
    doi: 10.1038/s41586-024-08106-4
  - type: dataset
    title: "Input dataset"
    doi: 10.5281/zenodo.200
"""


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "CITATION.cff").write_text(CFF)
    (tmp_path / "Snakefile").write_text("rule all:\n    input: 'results/summary.json'\n")
    (tmp_path / "pixi.toml").write_text("[workspace]\n")
    (tmp_path / "notebooks").mkdir()
    (tmp_path / "notebooks" / "03_analysis.py").write_text("# analysis\n")
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "summary.json").write_text('{"accuracy": 0.8}\n')
    (tmp_path / "figures").mkdir()
    (tmp_path / "figures" / "main_result.png").write_bytes(b"\x89PNG\r\n")
    rows = "\n".join(f"| 0{i} | Step {i} | [RA{i}]({NP}{i}abcdefghij) | 2026-10-04 |" for i in range(1, 7))
    (tmp_path / "nanopubs").mkdir()
    (tmp_path / "nanopubs" / "PUBLISHED.md").write_text(f"| Step | Template | URI | Published |\n|---|---|---|---|\n{rows}\n")
    return tmp_path


def graph(crate) -> dict:
    return {e["@id"]: e for e in crate.metadata.generate()["@graph"]}


def test_root_from_citation_cff(repo: Path) -> None:
    g = graph(build_rocrate.build(repo, {}))
    root = g["./"]
    assert g["ro-crate-metadata.json"]["conformsTo"]["@id"] == "https://w3id.org/ro/crate/1.2"
    assert root["name"] == "demo-replication: testing a headline claim"
    assert root["version"] == "1.2.0"  # from the newest version DOI, not the lagging version field
    assert root["mainEntity"]["@id"] == "Snakefile"
    assert g[root["identifier"]["@id"]]["url"] == "https://doi.org/10.5281/zenodo.102"
    assert root["sameAs"]["@id"] == "https://doi.org/10.5281/zenodo.100"
    assert root["author"]["@id"] == "https://orcid.org/0000-0002-1784-2920"


def test_files_chain_and_references(repo: Path) -> None:
    g = graph(build_rocrate.build(repo, {}))
    root = g["./"]
    parts = {p["@id"] for p in root["hasPart"]}
    assert {"Snakefile", "notebooks/03_analysis.py", "results/summary.json", "figures/main_result.png",
            "https://doi.org/10.5281/zenodo.200", "https://doi.org/10.5281/zenodo.102"} <= parts
    assert [s["@id"] for s in root["subjectOf"]] == [f"{NP}{i}abcdefghij" for i in range(1, 7)]
    assert root["citation"]["@id"] == "https://doi.org/10.1038/s41586-024-08106-4"
    # cited software would be read as a local script by the validator; articles stay articles
    assert g["https://doi.org/10.1038/s41586-024-08106-4"]["@type"] == "ScholarlyArticle"


def test_every_reference_is_described(repo: Path) -> None:
    g = graph(build_rocrate.build(repo, {}))
    for e in g.values():
        for v in e.values():
            for item in v if isinstance(v, list) else [v]:
                if isinstance(item, dict) and set(item) == {"@id"} and not item["@id"].startswith("#"):
                    assert item["@id"] in g or not item["@id"].startswith("http"), item["@id"]


def test_config_funding_place_and_cca(repo: Path) -> None:
    cfg = {"funding": [{"@id": "https://cordis.europa.eu/project/id/101188256", "name": "FAIR2Adapt",
                        "identifier": "101188256",
                        "funder": {"@id": "https://ror.org/00k4n6c32", "name": "European Commission"}}],
           "place": {"name": "Hamburg", "bbox": [9.7, 53.4, 10.3, 53.7]},
           "cca": {"sensitivity": "public", "data_collector": "https://orcid.org/0000-0002-1784-2920",
                   "source": "https://doi.org/10.5281/zenodo.200", "nature": "derived"}}
    g = graph(build_rocrate.build(repo, cfg))
    root = g["./"]
    assert root["funding"][0]["@id"] == "https://cordis.europa.eu/project/id/101188256"
    assert g["#study-area-box"]["box"] == "53.4 9.7 53.7 10.3"
    assert root["identifier"] == "https://doi.org/10.5281/zenodo.102"  # CCA wants a literal
    assert any(p["@id"] == build_rocrate.CCA_PROFILE for p in root["conformsTo"])


def test_before_first_release(repo: Path) -> None:
    cff = CFF.replace("doi: 10.5281/zenodo.100", 'doi: "{{CONCEPT_DOI}}"')
    cff = cff[:cff.index("identifiers:")] + cff[cff.index("references:"):]
    (repo / "CITATION.cff").write_text(cff)
    root = graph(build_rocrate.build(repo, {}))["./"]
    assert "identifier" not in root and "sameAs" not in root


def test_uninitialised_template_left_alone(repo: Path, monkeypatch, capsys) -> None:
    (repo / ".template-uninitialised").touch()
    monkeypatch.setattr(sys, "argv", ["build_rocrate.py", "--repo", str(repo)])
    assert build_rocrate.main() == 0
    assert not (repo / "ro-crate-metadata.json").exists()


def test_deposit_plan(repo: Path, monkeypatch) -> None:
    monkeypatch.setattr(deposit_rohub, "record_url",
                        lambda u: u.replace("https://doi.org/10.5281/zenodo.", "https://zenodo.org/records/"))
    monkeypatch.setattr(sys, "argv", ["build_rocrate.py", "--repo", str(repo)])
    build_rocrate.main()
    p = deposit_rohub.plan(repo, {"outcome_evidence": ["results/summary.json"], "sketch": "figures/main_result.png"})
    by_id = {r["id"]: r for r in p["resources"]}
    assert "ro-crate-metadata.json" not in by_id  # restricted name in ROHub
    assert by_id["Snakefile"]["res_type"] == "Computational workflow"
    assert by_id["https://doi.org/10.5281/zenodo.200"]["url"] == "https://zenodo.org/records/200"
    assert [l["url"] for l in p["links"] if l["res_type"] == "Nanopublication"] == \
        [f"{NP}{i}abcdefghij" for i in range(1, 7)]
    assert all(not l["url"].startswith("https://doi.org/10.5281") for l in p["links"])
    rels = {(r["source"], r["type"], r["destination"]) for r in p["relations"]}
    assert ("Snakefile", "hasInput", "https://doi.org/10.5281/zenodo.200") in rels
    assert ("Snakefile", "hasOutput", "results/summary.json") in rels
    assert ("Snakefile", "softwareRequirements", "pixi.toml") in rels
    assert (f"{NP}2abcdefghij", "wasDerivedFrom", f"{NP}1abcdefghij") in rels
    assert (f"{NP}5abcdefghij", "wasDerivedFrom", "results/summary.json") in rels
    assert p["license"] == "mit"
    assert p["authors"] == [{"display_name": "Anne Fouilloux", "orcid_id": "0000-0002-1784-2920"}]
