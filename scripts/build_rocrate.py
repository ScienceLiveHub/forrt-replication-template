#!/usr/bin/env python3
"""Regenerate ro-crate-metadata.json (RO-Crate 1.2) from this repository's own metadata.

    python scripts/build_rocrate.py            # writes ro-crate-metadata.json at the repo root
    python scripts/build_rocrate.py --print    # prints it instead

The crate describes the replication as a FAIR Digital Object, not a folder listing:

- identity, abstract, keywords, authors, licence and release identifiers from CITATION.cff
  (and codemeta.json for older repos without an abstract);
- the Snakefile as main workflow (or a Galaxy workflow, see rocrate.json), the notebooks,
  configuration and the small result files and figures, referenced in place (nothing is copied);
- the signed FORRT nanopublication chain from nanopubs/PUBLISHED.md (subjectOf);
- citations and input datasets from the references in CITATION.cff;
- what the repository cannot say about itself, from an optional rocrate.json: the community FAIR
  Implementation Profile (conformsTo), funding, study area, input datasets held elsewhere, and the
  CCA RO-Crate profile fields for climate-adaptation studies. See rocrate.example.json and
  docs/ro-crate.md.

CI rebuilds and validates it (rocrate-validator, profile ro-crate-1.2, REQUIRED level), so it
cannot drift from the repository. scripts/deposit_rohub.py deposits it in ROHub.
"""

from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from datetime import date
from pathlib import Path

import yaml
from rocrate.model.contextentity import ContextEntity
from rocrate.rocrate import ROCrate

ROOT = Path(__file__).resolve().parent.parent
CCA_PROFILE = "https://w3id.org/cca-crate-profile/0.9"
# Prefixes only: the CCA profile's published context redefines core terms with https://schema.org
# (FAIR2Adapt/cca-crate-profile#4), which would change the meaning of name, description, ...
CCA_PREFIXES = {"cca": "https://w3id.org/ro/terms/cca/", "dct": "http://purl.org/dc/terms/",
                "dpv": "https://w3id.org/dpv#", "citedcat": "https://w3id.org/citedcat-ap/",
                "iadopt": "https://w3id.org/iadopt/ont/"}
DEFAULT_INCLUDE = {
    "notebooks/0*.py": "Notebook {name} (jupytext)",
    "pixi.toml": "Pixi manifest: declared dependencies",
    "Dockerfile": "Container build specification",
    "results/*.csv": "Result table {name}",
    "results/*.json": "Result {name}",
    "results/*.nc": "Result {name} (NetCDF)",
    "figures/*.png": "Figure {name}",
}
MAX_INCLUDED_BYTES = 20_000_000  # larger results stay in the Zenodo release, referenced by its DOI
FMT = {".json": "application/json", ".csv": "text/csv", ".png": "image/png", ".pdf": "application/pdf",
       ".nc": "application/x-netcdf", ".py": "text/x-python", ".md": "text/markdown", ".ga": "application/json",
       ".toml": "application/toml", ".lock": "application/yaml", ".parquet": "application/vnd.apache.parquet"}
STEP_NAMES = {"01": "Quote / research question", "02": "AIDA sentence", "03": "FORRT claim",
              "04": "FORRT replication study", "05": "FORRT replication outcome", "06": "CiTO citation"}


def ref(crate: ROCrate, uri: str, props: dict) -> ContextEntity:
    return crate.add(ContextEntity(crate, uri, properties=props))


def doi_url(value: str) -> str:
    return value if value.startswith("http") else f"https://doi.org/{value}"


def chain_uris(repo: Path) -> list[tuple[str, str, str]]:
    """(step, template name, URI) rows of nanopubs/PUBLISHED.md; older repos list the chain in a README table."""
    rows = []
    ledger = repo / "nanopubs" / "PUBLISHED.md"
    for line in (ledger.read_text().splitlines() if ledger.exists() else []):
        m = re.match(r"\|\s*(0[1-6])\s*\|\s*([^|]+?)\s*\|[^|]*?(https://w3id\.org/(?:sciencelive/)?np/RA[\w-]+)", line)
        if m:
            rows.append(m.groups())
    readme = repo / "README.md"
    if not rows and readme.exists():
        for line in readme.read_text().splitlines():
            m = re.match(r"\|\s*([1-6])\s*\|\s*([^|]+?)\s*\|.*\((https://w3id\.org/(?:sciencelive/)?np/RA[\w-]+)\)", line)
            if m:
                rows.append((f"0{m.group(1)}", re.sub(r"\s*\(.*", "", m.group(2)).strip("* "), m.group(3)))
    return rows


def release_ids(cff: dict, doi: str | None = None) -> tuple[str | None, str | None, str | None]:
    """Concept DOI, newest version DOI, newest SWHID (set_release_identifiers.py lists newest first).
    Older repos record only a concept DOI; before the first release there is none."""
    ids = cff.get("identifiers") or []
    concept = doi or cff.get("doi")
    if concept and "{{" in str(concept):
        concept = None
    version = next((i["value"] for i in ids if i.get("type") == "doi" and "Version DOI" in i.get("description", "")),
                   concept)
    swh = next((i["value"] for i in ids if i.get("type") == "swh"), None)
    return (doi_url(concept) if concept else None, doi_url(version) if version else None, swh)


def release_version(cff: dict) -> str:
    """Version of the newest release, from its DOI entry (the top-level version field can lag behind)."""
    for i in cff.get("identifiers") or []:
        m = re.search(r"Version DOI for v(\S+)", i.get("description", ""))
        if m:
            return m.group(1)
    return str(cff.get("version", "0.0.0"))


def snakemake_version(repo: Path) -> str:
    """The Snakemake build pinned in pixi.lock (pixi.toml only says "*"); older conda repos do not pin it."""
    lock = repo / "pixi.lock"
    found = re.findall(r"/snakemake-(\d+\.\d+\.\d+)-", lock.read_text()) if lock.exists() else []
    return max(found, key=lambda v: tuple(map(int, v.split(".")))) if found else "not pinned"


def add_files(crate: ROCrate, repo: Path, cfg: dict) -> None:
    snake = ref(crate, "https://w3id.org/workflowhub/workflow-ro-crate#snakemake", {
        "@type": "ComputerLanguage", "name": "Snakemake", "version": snakemake_version(repo),
        "url": {"@id": "https://snakemake.readthedocs.io/"}})
    wf = crate.add_file(repo / "Snakefile", dest_path="Snakefile", properties={
        "@type": ["File", "SoftwareSourceCode", "ComputationalWorkflow"], "name": "Snakefile",
        "description": "Replication pipeline (Snakemake): download, clean, analyse, figures.",
        "programmingLanguage": snake, "encodingFormat": "text/x-snakemake",
        "contentSize": str((repo / "Snakefile").stat().st_size)})
    crate.root_dataset["mainEntity"] = wf
    if cfg.get("main_workflow"):  # a Galaxy workflow is the study's workflow; the Snakefile only orchestrates
        galaxy = ref(crate, "https://w3id.org/workflowhub/workflow-ro-crate#galaxy", {
            "@type": "ComputerLanguage", "name": "Galaxy", "version": cfg.get("galaxy_version", "unspecified"),
            "url": {"@id": "https://galaxyproject.org/"}})
        mw = cfg["main_workflow"]
        crate.root_dataset["mainEntity"] = crate.add_file(repo / mw, dest_path=mw, properties={
            "@type": ["File", "SoftwareSourceCode", "ComputationalWorkflow"], "name": mw,
            "description": cfg.get("main_workflow_description", "Galaxy workflow of the study."),
            "programmingLanguage": galaxy, "encodingFormat": "application/json",
            "contentSize": str((repo / mw).stat().st_size)})  # add_file lists it in hasPart
    for pattern, desc in cfg.get("include", DEFAULT_INCLUDE).items():
        for f in sorted(glob.glob(str(repo / pattern))):
            path = Path(f)
            if path.stat().st_size > MAX_INCLUDED_BYTES:
                continue
            rel = str(path.relative_to(repo))
            props = {"name": rel, "description": desc.replace("{name}", path.stem),
                     "encodingFormat": FMT.get(path.suffix, "text/plain"), "contentSize": str(path.stat().st_size)}
            if cfg.get("results_license") and rel.startswith(("results/", "figures/")):
                props["license"] = {"@id": cfg["results_license"]["@id"]}
            crate.add_file(f, dest_path=rel, properties=props)


def references(cff: dict) -> tuple[list[dict], list[dict]]:
    """CITATION.cff references -> (input datasets, citations). Datasets and databases are inputs."""
    inputs, cites = [], []
    for r in cff.get("references") or []:
        ident = r.get("doi") or r.get("url")
        if not ident or "{{" in str(ident):
            continue
        url, title = doi_url(str(ident)), str(r.get("title", ident))[:240]
        if r.get("type") in ("dataset", "database", "data"):
            inputs.append({"@id": url, "@type": "File", "name": title})
        else:  # typed CreativeWork, not SoftwareSourceCode: the validator reads a code URL as a local script
            cites.append({"@id": url, "@type": "ScholarlyArticle" if r.get("type") == "article" else "CreativeWork",
                          "name": title})
    return inputs, cites


def add_people(crate: ROCrate, cff: dict) -> list:
    people = []
    for a in cff.get("authors") or []:
        name = f"{a.get('given-names', '')} {a.get('family-names', '')}".strip() or a.get("name", "")
        uri = a.get("orcid") if a.get("orcid") and "{{" not in a["orcid"] else f"#{re.sub(r'\W+', '-', name).lower()}"
        props = {"@type": "Person", "name": name}
        if a.get("affiliation"):
            props["affiliation"] = a["affiliation"]
        people.append(ref(crate, uri, props))
    return people


def add_cca(crate: ROCrate, c: dict, place) -> None:
    """Root-level fields the CCA profile requires of every Dataset (DatasetShape)."""
    root = crate.root_dataset
    level = ref(crate, "#sensitivity", {"@type": ["DefinedTerm", "dpv:SensitivityLevel"], "name": c["sensitivity"]})
    root["citedcat:dataCollector"] = {"@id": c["data_collector"]}
    root["dct:source"] = c["source"]
    root["cca:dataNature"] = c["nature"]
    root["dpv:hasSensitivityLevel"] = level
    if place:
        root["spatialCoverage"] = place


def name_referenced(crate: ROCrate, names: dict) -> None:
    """Give a type and name to every URI the crate points to but does not describe."""
    named = {"https://snakemake.readthedocs.io/": "Snakemake documentation",
             "https://galaxyproject.org/": "Galaxy", **names}
    seen = {e.id for e in crate.get_entities()}
    for e in list(crate.get_entities()):
        for v in e.properties().values():
            for item in (v if isinstance(v, list) else [v]):
                if isinstance(item, dict) and set(item) == {"@id"} and item["@id"] not in seen \
                        and item["@id"].startswith("http"):
                    ref(crate, item["@id"], {"@type": "CreativeWork", "name": named.get(item["@id"], item["@id"])})
                    seen.add(item["@id"])


def build(repo: Path, cfg: dict) -> ROCrate:
    cff = yaml.safe_load((repo / "CITATION.cff").read_text())
    codemeta = json.loads((repo / "codemeta.json").read_text()) if (repo / "codemeta.json").exists() else {}
    concept, version, swh = release_ids(cff, cfg.get("doi"))
    crate = ROCrate(version="1.2")
    cca = cfg.get("cca")
    if cca:
        crate.metadata.extra_terms.update(CCA_PREFIXES)
    add_files(crate, repo, cfg)
    root = crate.root_dataset

    ref_inputs, ref_cites = references(cff)
    for inp in cfg.get("inputs", ref_inputs):
        props = {"description": inp["name"], "encodingFormat": "text/html", "sdDatePublished": date.today().isoformat(),
                 **{k: v for k, v in inp.items() if k != "@id"}}
        root.append_to("hasPart", ref(crate, inp["@id"], props))

    people = add_people(crate, cff)
    root["name"] = cfg.get("title", cff.get("title"))
    root["description"] = " ".join(str(cfg.get("description") or cff.get("abstract")
                                       or codemeta.get("description") or root["name"]).split())
    if people:
        root["author"] = people if len(people) > 1 else people[0]
    licence = cff.get("license", "MIT")
    root["license"] = ref(crate, f"https://spdx.org/licenses/{licence}", {
        "@type": "CreativeWork", "name": f"{licence} License", "description": f"{licence} licence for the code."})
    if cfg.get("results_license"):
        rl = cfg["results_license"]
        ref(crate, rl["@id"], {"@type": "CreativeWork", "name": rl["name"],
                               "description": "Licence of the derived results and figures."})
    root["datePublished"] = str(cff.get("date-released") or codemeta.get("datePublished") or date.today().isoformat())
    root["version"] = release_version(cff)
    root["keywords"] = cff.get("keywords") or []
    root["codeRepository"] = cff.get("repository-code") or codemeta.get("codeRepository")

    grants = []
    for g in cfg.get("funding", []):
        funder = ref(crate, g["funder"]["@id"], {"@type": "Organization", "name": g["funder"]["name"]})
        grants.append(ref(crate, g["@id"], {"@type": "Grant", "name": g["name"], "identifier": g["identifier"],
                                            "funder": {"@id": funder.id}}))
    if grants:
        root["funding"] = grants
        root["funder"] = [{"@id": g["funder"]["@id"]} for g in grants]

    profile_types = ["CreativeWork", "Profile"] + (["dct:Standard"] if cca else [])
    profiles = [ref(crate, p["@id"], {"@type": profile_types, **{k: v for k, v in p.items() if k != "@id"}})
                for p in cfg.get("profiles", [])]
    if cca and not any(p.id == CCA_PROFILE for p in profiles):
        profiles.append(ref(crate, CCA_PROFILE, {"@type": profile_types, "name": "Climate Change Adaptation RO-Crate "
                                                 "Profile (FAIR2Adapt)", "version": "0.9.0"}))
    if profiles:
        root["conformsTo"] = profiles

    place = None
    if cfg.get("place"):
        w, s, e, n = cfg["place"]["bbox"]
        place = ref(crate, "#study-area", {"@type": "Place", "name": cfg["place"]["name"], "geo": {"@id": "#study-area-box"}})
        ref(crate, "#study-area-box", {"@type": "GeoShape", "name": f"Bounding box of {cfg['place']['name']}",
                                       "box": f"{s} {w} {n} {e}"})
        root["contentLocation"] = place

    if cfg.get("project"):
        pj = cfg["project"]
        root["publisher"] = ref(crate, pj["@id"], {"@type": ["Organization", "Project"], "name": pj["name"], "url": pj["@id"]})
    elif cfg.get("publisher"):
        pb = cfg["publisher"]
        root["publisher"] = ref(crate, pb["@id"], {"@type": "Organization", "name": pb["name"]})
    elif people:
        root["publisher"] = {"@id": people[0].id}

    if version:
        # CCA wants a literal identifier; RO-Crate 1.2 recommends a PropertyValue
        root["identifier"] = version if cca else ref(crate, "#version-doi", {
            "@type": "PropertyValue", "name": "Version DOI", "propertyID": "https://registry.identifiers.org/registry/doi",
            "value": version.removeprefix("https://doi.org/"), "url": version})
        ref(crate, version, {"@type": "CreativeWork", "name": f"Release v{release_version(cff)} (Zenodo version DOI)",
                             "description": "Archived release: full source tree, results and figures.",
                             "license": {"@id": root["license"].id}})
        root.append_to("hasPart", crate.get(version))
    if concept and concept != version:
        root["sameAs"] = ref(crate, concept, {"@type": "CreativeWork", "name": "Concept DOI (all versions, Zenodo)"})
    if swh:
        ref(crate, swh, {"@type": "CreativeWork", "name": f"Source code of v{release_version(cff)} (Software Heritage)",
                         "codeRepository": root["codeRepository"]})
        root["isBasedOn"] = {"@id": swh}

    chain = [ref(crate, uri, {"@type": "CreativeWork", "additionalType": "Nanopublication",
                              "name": f"{STEP_NAMES.get(step, name)} (FORRT chain step {step})",
                              "encodingFormat": "application/trig"}) for step, name, uri in chain_uris(repo)]
    if chain:
        root["subjectOf"] = chain
    cites = [ref(crate, c["@id"], {k: v for k, v in c.items() if k != "@id"}) for c in cfg.get("citations", ref_cites)]
    if cites:
        root["citation"] = cites if len(cites) > 1 else cites[0]
    name_referenced(crate, cfg.get("names", {}))
    if cca:
        add_cca(crate, cca, place)
    return crate


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", type=Path, default=ROOT)
    ap.add_argument("--config", type=Path, default=None, help="default: rocrate.json at the repo root, if present")
    ap.add_argument("--print", action="store_true", help="print the metadata instead of writing it")
    args = ap.parse_args()
    if (args.repo / ".template-uninitialised").exists():
        print("Template not initialised yet (run /init-template); ro-crate-metadata.json left as is.")
        return 0
    cfg_path = args.config or args.repo / "rocrate.json"
    cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
    metadata = json.dumps(build(args.repo, cfg).metadata.generate(), indent=2, ensure_ascii=False) + "\n"
    if args.print:
        sys.stdout.write(metadata)
    else:
        (args.repo / "ro-crate-metadata.json").write_text(metadata)
        print(f"wrote {args.repo / 'ro-crate-metadata.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
