#!/usr/bin/env python3
"""Build ``nanopubs/chain-draft.json`` — the pre-filled hand-off for the Science
Live FORRT-chain wizard. See ``docs/chain-draft-contract.md`` for the format.

This is the **producer** side of the contract, and it is deliberately a plain,
deterministic script — **no Claude, no network**. The whole point is to move the
publish phase off Claude tokens: the researcher's content was drafted once during
the replication; this reads that plus the repo's own metadata and emits one JSON
file the browser wizard consumes.

For each chain step it routes every field to exactly one place:

* **carry**    — the back-reference field the wizard fills from the previous
                 step's published URI (``project``/``aida``/``claim``/``study``/
                 ``work``). Never pre-filled here — the URI doesn't exist yet.
* **metadata** — filled from ``CITATION.cff``: the replicated paper's DOI
                 (``paper``/``source``/``cited``), the Zenodo **version** DOI
                 (``repo``), the release date (``date``), the repo URL.
* **manual**   — the judgment calls, i.e. the template's ``restricted_choice``
                 fields (claim type, validation status, confidence, CiTO
                 relation). Listed in ``manual`` for the wizard; not pre-filled.
* **content**  — the drafted prose (quote, methodology, conclusion, the id slug,
                 …). Read from ``nanopubs/drafts/0X_*.md``.

Placeholder values (unsubstituted ``{{TOKEN}}`` in an uninitialised template, or
empty draft fences) are omitted, per the contract: a field the repo can't fill is
simply absent and the wizard renders it empty.

Run (offline, no special deps beyond ruamel.yaml which CITATION.cff needs):

    pixi run -e tests python scripts/build_chain_draft.py     # writes nanopubs/chain-draft.json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from ruamel.yaml import YAML

SCHEMA_VERSION = "1.0"

# The 6-step FORRT backbone, in order. The step-1 anchor is whichever of the
# three alternates the replication kept (the drafter deletes the other two).
CORE_STEPS = ["02_aida", "03_claim", "04_study", "05_outcome", "06_citation"]
ANCHORS = {"01_quote": "paper-rooted", "01_pico": "pico", "01_pcc": "pcc"}
OPTIONAL_STEPS = ["07_research_software", "08_synthesis"]

# step -> the field the wizard fills from the previous step's published URI.
CARRY_FIELD = {
    "02_aida": "project", "03_claim": "aida", "04_study": "claim",
    "05_outcome": "study", "06_citation": "work",
}

# The optional side-branches (07/08) link back to NON-ADJACENT earlier steps, and
# a step may have several such links, so they get their own carry edges rather than
# the linear one-per-step hop. `field` is the platform component's field name (what
# the wizard injects the carried URI into); `placeholder` is the snapshot field id
# to skip when building this step (it differs from `field` for the repeatables,
# e.g. researchOutputs <- placeholder researchoutput). `mode`/`itemKey` tell the
# wizard the target shape. See docs/chain-draft-contract.md.
BACK_LINKS: dict[str, list[dict]] = {
    "07_research_software": [
        {"from": "03_claim", "field": "project", "placeholder": "project"},
        {"from": "05_outcome", "field": "researchOutputs",
         "placeholder": "researchoutput", "mode": "uriList"},
    ],
    "08_synthesis": [
        {"from": "05_outcome", "field": "sources", "placeholder": "source",
         "mode": "uriObjectList", "itemKey": "source"},
    ],
}


def carried_placeholders(step: str) -> set[str]:
    """Snapshot field ids that the wizard fills via carry-forward (skip here)."""
    skip = {CARRY_FIELD[step]} if step in CARRY_FIELD else set()
    skip.update(bl["placeholder"] for bl in BACK_LINKS.get(step, []))
    return skip

# Short slug per step, for the "Short URI suffix" id fields (<org>-<repo>-<step>).
STEP_SLUG = {
    "01_quote": "quote", "01_pico": "pico", "01_pcc": "pcc", "02_aida": "aida",
    "03_claim": "claim", "04_study": "study", "05_outcome": "outcome",
    "06_citation": "citation", "07_research_software": "software", "08_synthesis": "synthesis",
}

# The CiTO citation type suggested from the Outcome's validation status. Keyed by
# the validation-status vocabulary URI's final segment.
CITO = "http://purl.org/spar/cito/"
RELATION_FROM_STATUS = {
    "Validated": CITO + "confirms",
    "PartiallySupported": CITO + "qualifies",
    "Contradicted": CITO + "disputes",
    "Inconclusive": CITO + "discusses",
    "NotTested": CITO + "cites",
}

# Wikidata concept fields — (step, snapshot placeholder id) -> (form field name,
# is_array). The agent lists plain labels in the draft; we resolve each to a
# Wikidata {uri, label} the form can use. `disciplineSelection` is a single
# object (not an array); the rest are arrays. Form field names from the audit.
WIKIDATA_FIELDS = {
    ("02_aida", "topic"): ("topic", True),
    ("04_study", "keyword"): ("keywordSelection", True),
    ("04_study", "discipline"): ("disciplineSelection", False),
    ("08_synthesis", "topic"): ("topicSelection", True),
}


# --- metadata (CITATION.cff) ---------------------------------------------

def _clean(v) -> str | None:
    """A usable value, or None for empty / unsubstituted ``{{TOKEN}}`` placeholders."""
    v = (str(v) if v is not None else "").strip()
    return None if (not v or "{{" in v) else v


def _bare_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", doi).strip() or None


def load_citation(text: str) -> dict:
    """Extract the metadata the chain needs from CITATION.cff text."""
    data = YAML(typ="safe").load(text) or {}
    out: dict = {}
    out["repo_url"] = _clean(data.get("repository-code"))
    out["date_released"] = _clean(data.get("date-released"))

    for ref in data.get("references") or []:
        if ref.get("type") == "article":
            out["paper_doi"] = _bare_doi(_clean(ref.get("doi")))
            break

    # The release workflow appends a version-DOI identifier whose description
    # says "Version DOI"; the concept DOI's does not.
    for ident in data.get("identifiers") or []:
        if ident.get("type") == "doi" and "version doi" in (ident.get("description") or "").lower():
            out["version_doi"] = _bare_doi(_clean(ident.get("value")))
            break
    return out


def metadata_value(step: str, name: str, cff: dict) -> str | None:
    """The CITATION.cff-derived value for a metadata field, in the form its
    template expects (bare DOI where the template adds the prefix, full URL
    otherwise), or None if this field isn't metadata / the value is absent."""
    paper = cff.get("paper_doi")
    if name == "paper":                       # uri field, template adds https://doi.org/
        return paper
    if name in ("source", "cited"):           # external_uri, wants the full URL
        return f"https://doi.org/{paper}" if paper else None
    if name == "repo" or (step == "07_research_software" and name == "software"):
        v = cff.get("version_doi")
        return f"https://doi.org/{v}" if v else None
    if name == "date":
        return cff.get("date_released")
    if step == "07_research_software" and name == "repository":
        return cff.get("repo_url")
    return None


# --- published URIs (PUBLISHED.md) ---------------------------------------

_URI_RE = re.compile(r"https?://w3id\.org/(?:sciencelive/)?np/RA[A-Za-z0-9_-]{20,}")


def parse_published(text: str) -> dict:
    """Map ``NN`` -> published URI from the PUBLISHED.md table (``_not yet
    published_`` rows yield nothing)."""
    out: dict = {}
    for line in text.splitlines():
        m = re.match(r"\s*\|\s*(\d{2})\s*\|", line)
        if not m:
            continue
        uri = _URI_RE.search(line)
        if uri:
            out[m.group(1)] = uri.group(0)
    return out


# --- drafted content (nanopubs/drafts/0X_*.md) ---------------------------

_HEADING_RE = re.compile(r"^#{2,4}\s+(.*?)\s*$")


def parse_draft(text: str) -> dict:
    """Extract ``{normalised heading: value}`` for each field section of a draft.

    A field is a ``###`` heading followed by the first fenced ``` block in its
    section. Guidance code fences (which live under other headings or in
    block-quotes) are ignored because we only take the first fence *after a
    field heading and before the next heading*."""
    out: dict = {}
    current = None
    in_fence = False
    buf: list[str] = []
    captured_for_current = False

    def flush():
        nonlocal buf, captured_for_current
        if current is not None and not captured_for_current:
            val = "\n".join(buf).strip()
            if val:
                out[_norm(current)] = val
            captured_for_current = True
        buf = []

    for line in text.splitlines():
        h = _HEADING_RE.match(line)
        if h and not in_fence:
            current = h.group(1)
            captured_for_current = False
            buf = []
            continue
        if line.strip().startswith("```"):
            if in_fence:                       # closing fence
                in_fence = False
                flush()
            elif not captured_for_current:     # opening fence for this field
                in_fence = True
                buf = []
            continue
        if in_fence:
            buf.append(line)
    return out


_STRIP_PREFIXES = (
    "choose ", "select ", "describe ", "search for ", "plain-text ",
    "short uri suffix for ", "short uri suffix as ", "label/name of ",
    "the ", "your ",
)


def _norm(s: str) -> str:
    s = s.lower()
    s = re.sub(r"\([^)]*\)", "", s)            # drop "(text input, required)" etc.
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    changed = True
    while changed:
        changed = False
        for p in _STRIP_PREFIXES:
            if s.startswith(p):
                s = s[len(p):]
                changed = True
    return s.strip()


def draft_content(draft_text: str, field) -> str | None:
    """Best-effort value for one content field from a draft, matched by label."""
    sections = parse_draft(draft_text)
    key = _norm(field["label"])
    if key in sections:
        return _draft_clean(sections[key])
    # loose containment either way, for hand-authored headings that drift
    for hk, hv in sections.items():
        if hk and (hk in key or key in hk):
            return _draft_clean(hv)
    return None


def _draft_clean(v: str) -> str | None:
    v = v.strip()
    if not v or "{{" in v or v.startswith("<") or v.lower().startswith("_vocabulary"):
        return None
    return v


def _draft_sections(text: str) -> dict:
    """heading (normalised) -> raw section body (lines until the next heading)."""
    out: dict = {}
    current = None
    buf: list[str] = []
    for line in text.splitlines():
        h = _HEADING_RE.match(line)
        if h:
            if current is not None:
                out[_norm(current)] = "\n".join(buf)
            current, buf = h.group(1), []
        else:
            buf.append(line)
    if current is not None:
        out[_norm(current)] = "\n".join(buf)
    return out


def draft_choice(draft_text: str, field: dict) -> str | None:
    """The vocabulary URI the agent checked for a restricted_choice field.

    The draft records the choice as a ticked checkbox (``- [x] Label``). Match
    that label against the field's ``possible_values`` by normalised label or by
    the value URI's final segment — hand-authored drafts often use a short label
    (``Replication Study``) where the template's is longer (``Replication Study -
    replication with different …``)."""
    body = _draft_sections(draft_text).get(_norm(field["label"]))
    if body is None:
        key = _norm(field["label"])
        for hk, hv in _draft_sections(draft_text).items():
            if hk and (hk in key or key in hk):
                body = hv
                break
    if not body:
        return None
    m = re.search(r"^\s*[-*]\s*\[[xX]\]\s*(.+?)\s*$", body, re.M)
    if not m:
        return None
    checked = _norm(m.group(1))
    for c in field.get("possible_values", []):
        label = _norm(c["label"])
        seg = _norm(re.sub(r"[-_]", " ", c["uri"].rsplit("/", 1)[-1]))
        if checked in (label, seg) or label.startswith(checked) or seg == checked:
            return c["uri"]
    return None


def slug_for(step: str, org: str | None, repo: str | None) -> str | None:
    ident = [p for p in (org, repo) if p]
    if not ident:                       # no repo identity (uninitialised template)
        return None
    s = re.sub(r"[^a-z0-9-]+", "-", "-".join([*ident, STEP_SLUG[step]]).lower()).strip("-")
    return s or None


def draft_labels(draft_text: str, field: dict) -> list[str]:
    """The plain labels the agent listed for a Wikidata field (best-effort).

    The draft lists them as bullets, optionally ``- _Label 1: <value>``. Take the
    text after a colon, or the bullet text, dropping empty/placeholder entries."""
    body = _draft_sections(draft_text).get(_norm(field["label"]))
    if body is None:
        key = _norm(field["label"])
        for hk, hv in _draft_sections(draft_text).items():
            if hk and (hk in key or key in hk):
                body = hv
                break
    if not body:
        return []
    out: list[str] = []
    for line in body.splitlines():
        m = re.match(r"\s*[-*]\s*_?[^:]*:\s*(.+?)\s*$", line) or re.match(r"\s*[-*]\s+(.+?)\s*$", line)
        if not m:
            continue
        v = m.group(1).strip().strip("_").strip()
        if v and v != "___" and "___" not in v and not v.startswith("<"):
            out.append(v)
    return out


def resolve_wikidata(label: str, *, timeout: int = 15) -> dict | None:
    """Resolve a label to a Wikidata ``{uri, label}`` via wbsearchentities (first
    match), or None. Network; failures return None so the generator degrades to
    leaving the field empty."""
    import urllib.parse
    import urllib.request
    q = urllib.parse.urlencode({
        "action": "wbsearchentities", "language": "en", "format": "json",
        "limit": "1", "search": label,
    })
    try:
        with urllib.request.urlopen(
                "https://www.wikidata.org/w/api.php?" + q, timeout=timeout) as r:
            hits = json.loads(r.read().decode("utf-8")).get("search") or []
    except Exception:  # noqa: BLE001
        return None
    if not hits:
        return None
    h = hits[0]
    return {
        "uri": h.get("concepturi") or f"http://www.wikidata.org/entity/{h['id']}",
        "label": h.get("label") or label,
    }


# --- assembly ------------------------------------------------------------

def is_metadata_field(step: str, name: str) -> bool:
    """Whether a field is filled from CITATION.cff (structurally — independent of
    whether the value is present in this repo)."""
    if name in ("paper", "source", "cited", "repo", "date"):
        return True
    return step == "07_research_software" and name in ("software", "repository")


def is_content_field(step: str, idx: int, f: dict) -> bool:
    """Content = drafted prose. Literals and the AIDA sentence are always content;
    a bare ``uri`` field is content only when it's the step's id slug (the first
    field) and not itself a metadata field. Optional topic/keyword/dataset URIs
    are left for the user (omitted)."""
    if f["kind"] in ("literal", "long_literal", "auto_escape_uri"):
        return True
    if f["kind"] == "uri":
        return idx == 0 and not is_metadata_field(step, f["id"])
    return False


def _org_repo(repository: str) -> tuple[str | None, str | None]:
    m = re.search(r"github\.com[:/]+([^/]+)/([^/]+?)(?:\.git)?/?$", repository or "")
    return (m.group(1), m.group(2)) if m else (None, None)


def _finish(step, registry_meta, prefill, provenance, manual, published_uri) -> dict:
    out = {
        "step": step,
        "template_key": registry_meta["key"],
        "template_uri": registry_meta["current"],
        "prefill": prefill,
    }
    if provenance:
        out["provenance"] = provenance
    if manual:
        out["manual"] = manual
    out["published_uri"] = published_uri
    return out


def build_step(step: str, spec: dict, registry_meta: dict, cff: dict,
               draft_text: str | None, published_uri: str | None, *,
               org: str | None = None, repo: str | None = None,
               cito_relation: str | None = None, resolve=None) -> dict:
    prefill: dict = {}
    provenance: dict = {}
    manual: list[str] = []

    # The CiTO citation is a REQUIRED repeatable group. Its form field is `st02`,
    # an array of {cites, cited} — not flat cites/cited (see the component audit in
    # docs/chain-draft-contract.md). Prepare one row: the relation suggested from
    # the Outcome's validation status, cited = the replicated paper.
    if step == "06_citation":
        row: dict = {}
        if cito_relation:
            row["cites"] = cito_relation
        paper = metadata_value(step, "cited", cff)
        if paper:
            row["cited"] = paper
        if row:
            prefill["st02"] = [row]
            provenance["st02"] = ("cites = validation status (see 05_outcome); "
                                  "cited = CITATION.cff references[article]")
        return _finish(step, registry_meta, prefill, provenance, manual, published_uri)

    carried = carried_placeholders(step)
    for idx, f in enumerate(spec["fields"]):
        name = f["id"]
        if name in carried:
            continue                                   # wizard fills from a prior URI
        if f["kind"] == "restricted_choice":
            manual.append(name)                        # flag: agent's call, confirm it
            choice = draft_choice(draft_text, f) if draft_text else None
            if choice is not None:
                prefill[name] = choice                 # ...but pre-fill the recorded choice
                provenance[name] = f"nanopubs/drafts/{step}.md"
            continue
        wk = WIKIDATA_FIELDS.get((step, name))
        if wk:                                         # Wikidata concept field
            form_field, is_array = wk
            items = []
            if draft_text and resolve is not None:
                for label in draft_labels(draft_text, f):
                    r = resolve(label)
                    if r:
                        items.append(r)
            if items:
                prefill[form_field] = items if is_array else items[0]
                provenance[form_field] = f"nanopubs/drafts/{step}.md + Wikidata"
            continue
        mv = metadata_value(step, name, cff)
        if mv is not None:
            prefill[name] = mv
            provenance[name] = "CITATION.cff"
            continue
        if is_content_field(step, idx, f):
            val = draft_content(draft_text, f) if draft_text else None
            prov = f"nanopubs/drafts/{step}.md"
            if val is None and idx == 0 and f["kind"] == "uri":   # the id slug
                val = slug_for(step, org, repo)
                prov = "derived (<org>-<repo>-<step>)"
            if val is not None:
                prefill[name] = val
                provenance[name] = prov

    return _finish(step, registry_meta, prefill, provenance, manual, published_uri)


def detect_anchor(drafts_dir: Path) -> str:
    present = [a for a in ANCHORS if (drafts_dir / f"{a}.md").exists()]
    if len(present) == 1:
        return present[0]
    # Uninitialised template keeps all three; default to paper-rooted.
    return "01_quote"


def build_chain_draft(repo_root: Path, *, repository: str, commit: str,
                      resolve_wikidata=resolve_wikidata) -> dict:
    templates = repo_root / "nanopubs" / "templates"
    registry = json.loads((templates / "registry.json").read_text())
    snapshot = json.loads((templates / "fields.snapshot.json").read_text())["steps"]
    drafts_dir = repo_root / "nanopubs" / "drafts"

    cff_path = repo_root / "CITATION.cff"
    cff = load_citation(cff_path.read_text()) if cff_path.exists() else {}
    pub_path = repo_root / "nanopubs" / "PUBLISHED.md"
    published = parse_published(pub_path.read_text()) if pub_path.exists() else {}

    anchor = detect_anchor(drafts_dir)
    step_ids = [anchor] + CORE_STEPS
    for opt in OPTIONAL_STEPS:                     # append only if actually drafted
        p = drafts_dir / f"{opt}.md"
        if p.exists() and draft_has_content(p.read_text(), snapshot.get(opt, {})):
            step_ids.append(opt)

    org, repo = _org_repo(repository)
    steps = []
    outcome_status: str | None = None
    for step in step_ids:
        if step not in snapshot:
            continue
        dp = drafts_dir / f"{step}.md"
        # The citation type is suggested from the Outcome's validation status.
        relation = None
        if step == "06_citation" and outcome_status:
            relation = RELATION_FROM_STATUS.get(outcome_status.rsplit("/", 1)[-1])
        st = build_step(
            step, snapshot[step], registry["steps"][step], cff,
            dp.read_text() if dp.exists() else None, published.get(step[:2]),
            org=org, repo=repo, cito_relation=relation, resolve=resolve_wikidata,
        )
        if step == "05_outcome":
            outcome_status = st["prefill"].get("validationStatus")
        steps.append(st)

    carry = [{"from": a, "into": b, "field": CARRY_FIELD[b]}
             for a, b in zip(step_ids, step_ids[1:]) if b in CARRY_FIELD]
    present = set(step_ids)
    for target, links in BACK_LINKS.items():                # side-branch back-links
        if target not in present:
            continue
        for bl in links:
            if bl["from"] not in present:
                continue
            edge = {"from": bl["from"], "into": target, "field": bl["field"]}
            for k in ("mode", "itemKey"):
                if k in bl:
                    edge[k] = bl[k]
            carry.append(edge)

    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "forrt-chain-draft",
        "chain_shape": ANCHORS[anchor],
        "source": {"repository": repository, "commit": commit},
        "steps": steps,
        "carry_forward": carry,
    }


def draft_has_content(text: str, spec: dict) -> bool:
    return any(
        draft_content(text, f) is not None
        for i, f in enumerate(spec.get("fields", []))
        if is_content_field("", i, f)
    )


def _git(repo_root: Path, *args: str, default: str = "") -> str:
    try:
        return subprocess.run(["git", "-C", str(repo_root), *args],
                              capture_output=True, text=True, timeout=10).stdout.strip() or default
    except Exception:  # noqa: BLE001
        return default


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--repo-root", default=".", help="Repository root (default: cwd).")
    p.add_argument("-o", "--out", default=None,
                   help="Output path (default: <repo-root>/nanopubs/chain-draft.json).")
    args = p.parse_args(argv)

    root = Path(args.repo_root).resolve()
    repo_url = _git(root, "config", "--get", "remote.origin.url",
                    default=f"https://github.com/OWNER/{root.name}")
    repo_url = re.sub(r"^git@github\.com:", "https://github.com/", repo_url)
    repo_url = re.sub(r"\.git$", "", repo_url)
    commit = _git(root, "rev-parse", "HEAD", default="HEAD")

    draft = build_chain_draft(root, repository=repo_url, commit=commit)
    out = Path(args.out) if args.out else root / "nanopubs" / "chain-draft.json"
    out.write_text(json.dumps(draft, indent=2, ensure_ascii=False) + "\n")

    filled = sum(len(s["prefill"]) for s in draft["steps"])
    print(f"Wrote {out} — {len(draft['steps'])} steps, {filled} fields pre-filled "
          f"({draft['chain_shape']}).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
