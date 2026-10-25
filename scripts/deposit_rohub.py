#!/usr/bin/env python3
"""Deposit this replication in ROHub as a complete Research Object, built from ro-crate-metadata.json.

    python scripts/build_rocrate.py                 # first: the crate must describe the current release
    python scripts/deposit_rohub.py --dry-run       # print what would be created, touch nothing
    ROHUB_USERNAME=... ROHUB_PASSWORD=... python scripts/deposit_rohub.py

The RO is created directly, with title, description, type and research areas from the start, then filled:
the crate's local files become internal resources in their folders; its input datasets, release, nanopub
chain, profiles and citations become typed external resources; and the workflow's provenance becomes
ROHub relations (inputs, outputs, requirements, nanopub chain, evidence behind the Outcome).

ROHub's own RO-Crate import is deliberately not used: it leaves the description empty, so the RO is
flagged as spam and locked against every later edit, and it drops every entity that is not a File.

Settings ROHub needs and the crate does not hold go in the "rohub" block of rocrate.json:
    {"research_areas": ["Earth sciences"], "ros_type": "Workflow-centric Research Object",
     "authors": [{"username": "<ROHub login>"}], "sketch": "figures/main_result.png",
     "sketch_title": "...", "outcome_evidence": ["results/summary.json"]}
Authors default to the crate's authors (matched to ROHub accounts by ORCID). Funding, licence and
study area are read from the crate. Writes rohub-deposit.json with the RO id, PID and resource ids.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
# predicates ROHub uses for its relation types (read from relations made in its interface)
PREDICATES = {
    "hasInput": "http://purl.org/wf4ever/wfdesc#hasInput",
    "hasOutput": "http://purl.org/wf4ever/wfdesc#hasOutput",
    "softwareRequirements": "https://schema.org/softwareRequirements",
    "wasDerivedFrom": "http://www.w3.org/ns/prov#wasDerivedFrom",
}
RES_TYPE_BY_SUFFIX = {".ga": "Computational workflow", ".cwl": "Computational workflow", ".py": "Python Script",
                      ".png": "Figure", ".pdf": "Figure", ".json": "Result", ".csv": "Result", ".nc": "Result",
                      ".tif": "Dataset", ".zip": "File"}
LINK_TYPE = {"ScholarlyArticle": "Journal article", "CreativeWork": "Other", "SoftwareSourceCode": "Software source code",
             "Dataset": "Dataset"}


def short(title: str | None, limit: int = 250) -> str | None:
    """ROHub resource titles are limited to 250 characters."""
    return title if not title or len(title) <= limit else title[:limit - 1].rstrip() + "…"


def record_url(url: str) -> str:
    """Landing page for a DOI: a DOI URL makes ROHub's enrichment mistype the resource and drop our title."""
    m = re.match(r"https://doi\.org/10\.5281/zenodo\.(\d+)$", url)
    if m:
        return f"https://zenodo.org/records/{m.group(1)}"
    if url.startswith("https://doi.org/"):
        try:
            return requests.head(url, allow_redirects=True, timeout=30).url
        except requests.RequestException:
            return url
    return url


def types(e: dict) -> list:
    t = e.get("@type", [])
    return t if isinstance(t, list) else [t]


def ids_of(value) -> list[str]:
    return [v["@id"] for v in (value if isinstance(value, list) else [value] if value else [])]


def plan(repo: Path, cfg: dict) -> dict:
    """Everything to deposit, derived from the crate: resources, links, relations, metadata."""
    graph = {e["@id"]: e for e in json.loads((repo / "ro-crate-metadata.json").read_text())["@graph"]}
    root = graph[graph["ro-crate-metadata.json"]["about"]["@id"]]
    parts = ids_of(root.get("hasPart"))
    main_wf = root["mainEntity"]["@id"]
    if main_wf not in parts:
        parts.insert(0, main_wf)
    files = [p for p in parts if "File" in types(graph.get(p, {})) and p != "ro-crate-metadata.json"]
    local = [f for f in files if not f.startswith("http")]

    resources = [{"id": f, "res_type": "Computational workflow" if "ComputationalWorkflow" in types(graph[f])
                  else RES_TYPE_BY_SUFFIX.get(Path(f).suffix.lower(), "File"),
                  "title": short(graph[f].get("name", f)), "description": graph[f].get("description"),
                  "url": record_url(f) if f.startswith("http") else None} for f in files]

    links = []
    for uri in ids_of(root.get("subjectOf")):
        links.append({"res_type": "Nanopublication", "url": uri, "title": short(graph[uri]["name"]),
                      "description": "Signed nanopublication of the FORRT chain: what was claimed, how it was "
                                     "tested and how it held."})
    for uri in ids_of(root.get("conformsTo")):
        links.append({"res_type": "Nanopublication" if "/np/" in uri else "Software documentation", "url": uri,
                      "title": short(graph[uri].get("name", uri)), "description": "Profile this Research Object conforms to."})
    if root.get("codeRepository"):
        links.append({"res_type": "Software source code", "url": root["codeRepository"],
                      "title": f"{Path(root['codeRepository']).name} (source repository)"})
    version = next((p for p in parts if p.startswith("https://doi.org/") and p not in files), None)
    if version:
        links.append({"res_type": "Software", "url": record_url(version), "title": short(graph[version]["name"]),
                      "description": f"Archived release, DOI {version.removeprefix('https://doi.org/')}."})
    for uri in ids_of(root.get("citation")):
        links.append({"res_type": LINK_TYPE.get(types(graph[uri])[0], "Other"), "url": record_url(uri),
                      "title": short(graph[uri].get("name", uri))})

    rel = lambda s, t, d: {"source": s, "type": t, "destination": d}
    nps = ids_of(root.get("subjectOf"))
    relations = [rel(main_wf, "hasInput", f) for f in files if f.startswith(("http", "data/"))]
    relations += [rel(main_wf, "hasOutput", f) for f in local if f.startswith(("results/", "figures/"))]
    relations += [rel(main_wf, "softwareRequirements", f) for f in ("pixi.toml", "Dockerfile", "Snakefile")
                  if f in local and f != main_wf]
    relations += [rel(nps[i], "wasDerivedFrom", nps[i - 1]) for i in range(1, len(nps))]
    if len(nps) >= 5:  # the Outcome (step 05) rests on the result files that support it
        relations += [rel(nps[4], "wasDerivedFrom", e) for e in cfg.get("outcome_evidence", []) if e in local]

    funding = []
    for gid in ids_of(root.get("funding")):
        g = graph[gid]
        ror = g["funder"]["@id"].removeprefix("https://ror.org/")
        funding.append({"funder_ror": ror, "grant_number": g["identifier"], "grant_name": g["name"],
                        "funder_name": graph[g["funder"]["@id"]]["name"]})
    bbox = None
    for pid in ids_of(root.get("contentLocation")):
        box = graph.get(graph[pid].get("geo", {}).get("@id"), {}).get("box")
        if box:
            s, w, n, e = map(float, box.split())
            bbox = [w, s, e, n]
    authors = cfg.get("authors") or [{"display_name": graph[a]["name"], "orcid_id": a.removeprefix("https://orcid.org/")}
                                     for a in ids_of(root.get("author")) if a.startswith("https://orcid.org/")]
    licence = ids_of(root.get("license"))
    return {"title": root["name"], "description": root["description"],
            "research_areas": cfg.get("research_areas", ["Earth sciences"]),
            "ros_type": cfg.get("ros_type", "Workflow-centric Research Object"),
            "license": licence[0].rsplit("/", 1)[-1].lower() if licence else None, "authors": authors,
            "funding": funding, "bbox": bbox, "sketch": cfg.get("sketch"), "sketch_title": cfg.get("sketch_title"),
            "resources": resources, "links": links, "relations": relations}


def deposit(repo: Path, p: dict) -> dict:
    import rohub  # only needed for a real deposit
    from rohub import settings, utils

    def retry(fn, *args, tries: int = 6, wait: int = 15, **kwargs):
        """ROHub intermittently answers "does not exist" for an RO it has just created, and the rohub
        library exits on any HTTP error: retry."""
        for attempt in range(tries):
            try:
                return fn(*args, **kwargs)
            except SystemExit:
                if attempt == tries - 1:
                    raise
                time.sleep(wait)

    user = os.environ["ROHUB_USERNAME"]
    rohub.login(username=user, password=os.environ["ROHUB_PASSWORD"])
    started = time.time()
    try:
        ro_id = rohub.ros_create(title=p["title"], research_areas=p["research_areas"],
                                 description=p["description"], ros_type=p["ros_type"]).identifier
    except SystemExit:  # ROHub can answer 504 on create yet create the RO: find it by title
        ro_id = None
        for _ in range(10):
            time.sleep(30)
            r = utils.get_request(url=settings.API_URL + f"ros/?owner={user}&ordering=-created_on&page_size=10",
                                  use_token=True).json()
            since = time.strftime("%Y-%m-%dT%H:%M", time.gmtime(started - 120))
            ro_id = next((x["identifier"] for x in r.get("results", [])
                          if x["title"] == p["title"] and (x.get("created_on") or "") >= since), None)
            if ro_id:
                break
        if not ro_id:
            raise
    print("created", ro_id)

    ids: dict[str, str] = {}
    for folder in sorted({str(Path(r["id"]).parent) for r in p["resources"] if not r["url"] and "/" in r["id"]}):
        retry(rohub.ros_add_folders, ro_id, name=folder)
    for r in p["resources"]:
        if r["url"]:
            res = retry(rohub.ros_add_external_resource, ro_id, res_type=r["res_type"], input_url=r["url"],
                        title=r["title"], description=r["description"])
        else:
            res = retry(rohub.ros_add_internal_resource, ro_id, res_type=r["res_type"], file_path=str(repo / r["id"]),
                        title=r["title"], folder=str(Path(r["id"]).parent) if "/" in r["id"] else None,
                        description=r["description"])
        ids[r["id"]] = res.identifier

    agents = []
    for a in p["authors"]:
        if "username" in a:
            agents.append(a["username"])
            continue
        found = utils.get_request(url=settings.API_URL + f"users/?search={a['orcid_id']}").json().get("results", [])
        agents.append(found[0]["username"] if found else {"agent_type": "user", **a})
    if agents:
        retry(rohub.ros_set_authors, ro_id, agents)
    if p["license"]:
        retry(rohub.ros_set_license, ro_id, p["license"])
    for f in p["funding"]:
        # ROHub's own convention (as in ROs made in its interface): grant id = "<funder ROR>::<grant number>"
        retry(rohub.ros_add_funding, ro_id, grant_identifier=f"{f['funder_ror']}::{f['grant_number']}",
              grant_name=f["grant_name"], funder_name=f["funder_name"], funder_doi=f["funder_ror"])
    if p["bbox"]:
        w, s, e, n = p["bbox"]
        retry(rohub.ros_add_geolocation, ro_id, {"type": "FeatureCollection", "features": [{
            "type": "Feature", "properties": {},
            "geometry": {"type": "Polygon", "coordinates": [[[w, s], [e, s], [e, n], [w, n], [w, s]]]}}]})
    if p["sketch"]:
        res = retry(rohub.ros_add_internal_resource, ro_id, res_type="Sketch", file_path=str(repo / p["sketch"]),
                    title=short(p["sketch_title"]))
        ids[p["sketch"]] = res.identifier
    for link in p["links"]:
        res = retry(rohub.ros_add_external_resource, ro_id, res_type=link["res_type"], input_url=link["url"],
                    title=link["title"], description=link.get("description"))
        ids.setdefault(link["url"], res.identifier)
    # a relation is an annotation on the source resource whose body is {property: predicate, value: destination}
    uri = lambda key: f"https://w3id.org/ro-id/{ro_id}/resources/{ids[key]}"
    for r in p["relations"]:
        if r["source"] in ids and r["destination"] in ids:
            retry(rohub.ros_add_annotations, ro_id, resources=[ids[r["source"]]],
                  body_specification_json=[{"property": PREDICATES[r["type"]], "value": uri(r["destination"])}])
    return {"id": ro_id, "pid": f"https://w3id.org/ro-id/{ro_id}", "resources": ids}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", type=Path, default=ROOT)
    ap.add_argument("--config", type=Path, default=None, help="default: rocrate.json at the repo root, if present")
    ap.add_argument("--dry-run", action="store_true", help="print the deposit plan and stop")
    args = ap.parse_args()
    cfg_path = args.config or args.repo / "rocrate.json"
    cfg = json.loads(cfg_path.read_text()).get("rohub", {}) if cfg_path.exists() else {}
    p = plan(args.repo, cfg)
    if args.dry_run:
        print(json.dumps(p, indent=2, ensure_ascii=False))
        print(f"\n{len(p['resources'])} resources, {len(p['links'])} links, {len(p['relations'])} relations",
              file=sys.stderr)
        return 0
    if not p["sketch"]:
        print("warning: no sketch set in rocrate.json; the RO will have no image", file=sys.stderr)
    out = deposit(args.repo, p)
    (args.repo / "rohub-deposit.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: out[k] for k in ("id", "pid")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
