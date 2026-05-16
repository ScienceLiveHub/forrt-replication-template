#!/usr/bin/env python3
"""Import a published FORRT nanopublication chain from a single entry URI.

Discovery is driven by the **Science Live platform's pre-built SPARQL
queries** against the KnowledgePixels nanopub-network endpoint, rather
than by hand-coded link-walking + heuristic step-type classification.
The platform already publishes the queries that answer the questions
this importer needs ("what nanopubs reference X?" / "what does X
reference?" / "what is X's template?"), and the network's
``npa:networkGraph`` admin graph indexes those edges natively.

The script copies three queries from
``science-live-platform/frontend/src/lib/queries/`` into the template's
``scripts/queries/`` directory at first commit; updates to those queries
on the SL platform side flow through by re-copying.

Usage::

    python3 scripts/import-nanopub-chain.py <NANOPUB-URI>

For example, to import the canonical Bombus apex CiTO Citation::

    python3 scripts/import-nanopub-chain.py \\
        https://w3id.org/sciencelive/np/RA1q6c0fG2bMbiozF8Az2UpIfzAzqp8hoVEl6QIzfUpH8

Output (under ``nanopubs/imported/``):

* ``trig/<RA-id>.trig``           — cached TriG for every fetched nanopub.
* ``constellation.json``          — structured graph summary:
                                      ``{ entry, nodes, edges, external_citations }``.
* ``cited_papers.txt``            — external (non-nanopub) URIs found in
                                      the assertion graphs (typically DOIs).

The follow-up step is for the orchestrating skill
(``import-from-nanopub``) to read ``constellation.json`` and write
``CHAIN_SUMMARY.md`` for use in Phase 1.

Dependencies: stdlib + ``rdflib``. Network access required (HTTP to
``query.knowledgepixels.com`` for SPARQL + to ``w3id.org`` for TriG).

Termination guards:

* ``--depth N`` (default 5) — BFS depth from the entry URI.
* ``--max-nodes M`` (default 80) — total nanopubs to fetch.
* ``--timeout T`` (default 30 s per request).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

try:
    from rdflib import ConjunctiveGraph, URIRef
except ImportError:  # pragma: no cover
    sys.stderr.write(
        "ERROR: this script needs `rdflib`. Install with `pip install rdflib` "
        "in the env that runs your other replication scripts.\n"
    )
    raise SystemExit(2)

# --- Platform endpoints (mirror science-live-platform/frontend/src/lib/sparql.ts) ---
NANOPUB_SPARQL_ENDPOINT_FULL = "https://query.knowledgepixels.com/repo/full"

QUERIES_DIR = Path(__file__).parent / "queries"

# --- URI matching --------------------------------------------------------

_NANOPUB_URI_RE = re.compile(
    r"^(https?://w3id\.org/(?:sciencelive/)?np/RA[A-Za-z0-9_-]{20,})"
)
_DOI_RE = re.compile(r"https?://doi\.org/10\.[0-9]+/[^\s\"<>]+", re.IGNORECASE)
_ORCID_RE = re.compile(r"https?://orcid\.org/0000-[0-9X-]+", re.IGNORECASE)


def canonical_nanopub_uri(any_uri: str) -> str | None:
    """Return the canonical nanopub base URI, stripping fragments and
    named-graph sub-paths."""
    m = _NANOPUB_URI_RE.match(any_uri)
    return m.group(1) if m else None


def resolver_url(uri: str) -> str:
    """Map a canonical nanopub URI to the W3ID resolver that returns TriG.

    The Science Live form ``https://w3id.org/sciencelive/np/RA...`` redirects
    to the platform's HTML viewer. The generic form ``https://w3id.org/np/RA...``
    resolves through the nanopub-network HTTP resolver and serves TriG.
    """
    return uri.replace("https://w3id.org/sciencelive/np/",
                        "https://w3id.org/np/")


# --- HTTP helpers --------------------------------------------------------

def fetch_trig(uri: str, timeout: int = 30) -> str:
    """Fetch a nanopub URI as TriG."""
    fetch = resolver_url(uri)
    req = urllib.request.Request(
        fetch,
        headers={
            "Accept": "application/trig, application/n-quads;q=0.9, */*;q=0.5",
            "User-Agent": "forrt-replication-template/import-nanopub-chain",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    stripped = body.lstrip().lower()
    if stripped.startswith("<!doctype html") or stripped.startswith("<html"):
        raise ValueError(
            f"Resolver returned HTML for {uri}; expected TriG. The URI form may "
            f"not be supported by the W3ID redirect — file an issue or use "
            f"the bare ``https://w3id.org/np/RA…`` form."
        )
    return body


def load_query(name: str) -> str:
    """Load a SPARQL query file from ``scripts/queries/``."""
    path = QUERIES_DIR / f"{name}.rq"
    if not path.exists():
        raise FileNotFoundError(
            f"SPARQL query file not found: {path}. "
            "These should be copied from "
            "`science-live-platform/frontend/src/lib/queries/`."
        )
    return path.read_text()


def substitute(query: str, **bindings: str) -> str:
    """Substitute placeholders in a SPARQL query.

    Two conventions match the SL platform's `sparql.ts`:

    - ``?_name``       → ``<URI>``   (URI substitution, used for
                                       graph-pattern subjects/objects)
    - ``${name}``      → ``URI``     (bare-string substitution, used inside
                                       ``STR()`` / ``CONTAINS()`` clauses)
    """
    out = query
    for name, value in bindings.items():
        out = out.replace(f"?_{name}", f"<{value}>")
        out = out.replace("${" + name + "}", value)
    return out


def sparql_query(query: str, timeout: int = 60) -> list[dict[str, str]]:
    """POST a SPARQL query, return a list of bindings dicts."""
    data = urllib.parse.urlencode({"query": query}).encode("utf-8")
    req = urllib.request.Request(
        NANOPUB_SPARQL_ENDPOINT_FULL,
        data=data,
        headers={
            "Accept": "application/sparql-results+json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "forrt-replication-template/import-nanopub-chain",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return [
        {k: v["value"] for k, v in row.items()}
        for row in result.get("results", {}).get("bindings", [])
    ]


# --- Template-label lookup (the only "type classification" the script needs) ---

_TEMPLATE_LABEL_CACHE: dict[str, str] = {}


def template_label(template_uri: str, *, fetch_timeout: int = 20) -> str:
    """Return a human-readable label for a nanopub template.

    Templates on the SL platform / nanopub network are themselves nanopubs.
    Their ``rdfs:label`` or ``dct:title`` names what the template represents
    (e.g. "AIDA Sentence", "FORRT Replication Outcome", "Citation with CiTO").
    """
    if not template_uri:
        return ""
    if template_uri in _TEMPLATE_LABEL_CACHE:
        return _TEMPLATE_LABEL_CACHE[template_uri]
    try:
        trig = fetch_trig(template_uri, timeout=fetch_timeout)
    except Exception:
        _TEMPLATE_LABEL_CACHE[template_uri] = ""
        return ""
    graph = ConjunctiveGraph()
    try:
        graph.parse(data=trig, format="trig")
    except Exception:
        _TEMPLATE_LABEL_CACHE[template_uri] = ""
        return ""
    # Prefer the template's own subject; fall back to any rdfs:label / dct:title.
    label_predicates = {
        "http://www.w3.org/2000/01/rdf-schema#label",
        "http://purl.org/dc/terms/title",
        "http://purl.org/dc/elements/1.1/title",
    }
    template_ref = URIRef(template_uri)
    label = ""
    for s, p, o in graph.triples((template_ref, None, None)):
        if str(p) in label_predicates:
            cand = str(o).strip()
            if cand:
                label = cand
                break
    if not label:
        for s, p, o in graph.triples((None, None, None)):
            if str(p) in label_predicates and not isinstance(o, URIRef):
                cand = str(o).strip()
                if cand:
                    label = cand
                    break
    # Strip the "Template: " self-descriptive prefix that SL/nanopub-network
    # templates carry — the platform uses it to label the template *itself*,
    # but our consumers want the step-type, not the meta-label.
    if label.startswith("Template: "):
        label = label[len("Template: "):]
    elif label.startswith("Template "):
        label = label[len("Template "):]
    _TEMPLATE_LABEL_CACHE[template_uri] = label
    return label


# --- Per-nanopub summarisation -------------------------------------------

@dataclass
class NodeSummary:
    uri: str
    step_type: str = ""          # human-readable, from template's rdfs:label
    template_uri: str = ""
    authors_orcid: list[str] = field(default_factory=list)
    plain_text_excerpts: list[str] = field(default_factory=list)
    raw_trig_path: str = ""


@dataclass
class EdgeSummary:
    source: str
    target: str
    relation: str


def parse_node(uri: str, trig_path: Path) -> NodeSummary:
    """Build a NodeSummary from a fetched TriG file."""
    node = NodeSummary(uri=uri, raw_trig_path=str(trig_path))
    graph = ConjunctiveGraph()
    try:
        graph.parse(source=str(trig_path), format="trig")
    except Exception:
        return node

    # Template URI → step-type label (uses the platform's own template registry).
    for s, p, o in graph.triples((None, None, None)):
        ps = str(p)
        if ps.endswith("wasCreatedFromTemplate"):
            node.template_uri = str(o)
            node.step_type = template_label(node.template_uri)
            break

    # ORCID authors
    for s, p, o in graph.triples((None, None, None)):
        os_ = str(o)
        if _ORCID_RE.match(os_) and os_ not in node.authors_orcid:
            node.authors_orcid.append(os_)

    # Plain-text excerpts (longest few literals — these are the substantive
    # content like Outcome conclusions, Study scopes, AIDA sentences).
    seen: set[str] = set()
    candidates: list[str] = []
    for s, p, o in graph.triples((None, None, None)):
        if isinstance(o, URIRef):
            continue
        val = str(o).strip()
        if len(val) < 12 or val in seen:
            continue
        if val.startswith("http://") or val.startswith("https://"):
            continue
        seen.add(val)
        candidates.append(val)
    candidates.sort(key=len, reverse=True)
    node.plain_text_excerpts = candidates[:4]

    return node


def cited_dois(trig_path: Path) -> set[str]:
    """Return all DOI URIs found anywhere in a fetched TriG file."""
    out: set[str] = set()
    text = trig_path.read_text(errors="replace")
    for m in _DOI_RE.finditer(text):
        out.add(m.group(0))
    return out


# --- SPARQL-driven discovery + TriG-based content extraction -------------

def find_outgoing_refs(uri: str) -> list[str]:
    """All nanopubs the entry references (downstream chain direction)."""
    q = substitute(load_query("references-from"), nanopubUri=uri)
    rows = sparql_query(q)
    return [r["np"] for r in rows if "np" in r]


def find_incoming_refs(uri: str) -> list[str]:
    """All nanopubs that reference the entry (upstream chain direction).
    Uses the SL platform's existing ``nanopub-references.rq`` verbatim."""
    q = substitute(load_query("nanopub-references"), nanopubUri=uri)
    rows = sparql_query(q)
    return [r["np"] for r in rows if "np" in r]


def discover_neighbours(uri: str) -> set[str]:
    """Bidirectional neighbour set: outgoing references + incoming references."""
    out: set[str] = set()
    for fn in (find_outgoing_refs, find_incoming_refs):
        try:
            for n in fn(uri):
                canon = canonical_nanopub_uri(n)
                if canon and canon != uri:
                    out.add(canon)
        except urllib.error.HTTPError as e:
            print(f"    ! SPARQL HTTP error: {e}", file=sys.stderr)
        except urllib.error.URLError as e:
            print(f"    ! SPARQL URL error: {e}", file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            print(f"    ! SPARQL unexpected error: {e}", file=sys.stderr)
    return out


# --- BFS using SPARQL neighbourhood --------------------------------------

def walk(entry_uri: str, depth_limit: int, max_nodes: int, timeout: int,
         cache_dir: Path) -> tuple[dict[str, NodeSummary], list[EdgeSummary], set[str]]:
    """BFS the citation graph from `entry_uri`, using SPARQL for neighbour
    discovery and HTTP TriG fetching for per-nanopub content extraction.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)

    nodes: dict[str, NodeSummary] = {}
    edges: list[EdgeSummary] = []
    externals: set[str] = set()
    visited: set[str] = set()
    queue: deque[tuple[str, int]] = deque([(entry_uri, 0)])

    while queue and len(nodes) < max_nodes:
        uri, depth = queue.popleft()
        if uri in visited:
            continue
        visited.add(uri)

        # 1. Fetch the TriG (caching)
        ra_id = uri.rsplit("/", 1)[-1]
        trig_path = cache_dir / f"{ra_id}.trig"
        if not trig_path.exists():
            print(f"  [{depth}] fetch TriG  {uri}", file=sys.stderr)
            try:
                trig_path.write_text(fetch_trig(uri, timeout=timeout))
            except Exception as e:  # noqa: BLE001
                print(f"    ! TriG fetch failed: {e}", file=sys.stderr)
                continue
            time.sleep(0.1)

        # 2. Parse into a NodeSummary
        node = parse_node(uri, trig_path)
        nodes[uri] = node
        externals |= cited_dois(trig_path)

        # Templates and template-definition nanopubs are not chain steps;
        # don't crawl outward from them. After we've stripped the
        # "Template: " self-descriptive prefix in `template_label()`, the
        # remaining signature words for template-definition nanopubs are
        # "defining a/an" (assertion / provenance / pubinfo template) and
        # "publishing labels".
        label_lower = (node.step_type or "").lower()
        is_template = (
            label_lower.startswith("defining a") or
            label_lower.startswith("defining an") or
            "publishing labels" in label_lower
        )

        # 3. Discover neighbours via SPARQL (only if we still have depth budget,
        # and only if this node is itself a chain step, not a template).
        if depth < depth_limit and not is_template:
            print(f"  [{depth}] SPARQL nbrs {uri}", file=sys.stderr)
            try:
                neighbours = discover_neighbours(uri)
            except Exception as e:  # noqa: BLE001
                print(f"    ! neighbour discovery failed: {e}", file=sys.stderr)
                neighbours = set()
            # Exclude template URIs the node was created from — those are
            # template definitions, not chain steps. Same for any URI that
            # appears anywhere as the target of `wasCreatedFromTemplate`.
            template_targets = {node.template_uri} if node.template_uri else set()
            for n in neighbours:
                if n in template_targets:
                    continue
                edges.append(EdgeSummary(source=uri, target=n, relation="refersTo"))
                if n not in visited:
                    queue.append((n, depth + 1))

    return nodes, edges, externals


# --- Output --------------------------------------------------------------

def write_constellation(nodes: dict[str, NodeSummary],
                         edges: list[EdgeSummary],
                         entry_uri: str,
                         externals: set[str],
                         out_path: Path) -> None:
    payload = {
        "entry": entry_uri,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "sparql_endpoint": NANOPUB_SPARQL_ENDPOINT_FULL,
        "nodes": [
            {
                "uri": n.uri,
                "step_type": n.step_type,
                "template_uri": n.template_uri,
                "authors_orcid": n.authors_orcid,
                "plain_text_excerpts": n.plain_text_excerpts,
                "raw_trig_path": n.raw_trig_path,
            }
            for n in nodes.values()
        ],
        "edges": [
            {"source": e.source, "target": e.target, "relation": e.relation}
            for e in edges
        ],
        "external_citations": sorted(externals),
    }
    out_path.write_text(json.dumps(payload, indent=2))


# --- CLI -----------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Walk a published FORRT nanopub chain from a single entry "
                    "URI, using the Science Live platform's pre-built SPARQL "
                    "queries against the KP nanopub-network endpoint.",
    )
    p.add_argument("uri", help="Entry nanopub URI (e.g. CiTO or Research Synthesis).")
    p.add_argument("--depth", type=int, default=5,
                   help="BFS depth limit (default 5).")
    p.add_argument("--max-nodes", type=int, default=80,
                   help="Total nanopubs to fetch (default 80).")
    p.add_argument("--timeout", type=int, default=30,
                   help="HTTP timeout per fetch in seconds (default 30).")
    p.add_argument("--out-dir", default="nanopubs/imported",
                   help="Output directory (default 'nanopubs/imported').")
    args = p.parse_args(argv)

    canon = canonical_nanopub_uri(args.uri)
    if canon is None:
        print(f"ERROR: {args.uri!r} does not look like a nanopub URI.",
              file=sys.stderr)
        return 2
    if canon != args.uri:
        print(f"  normalised entry URI: {canon}", file=sys.stderr)
    args.uri = canon

    out_dir = Path(args.out_dir)
    cache_dir = out_dir / "trig"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Importing nanopub chain from {args.uri}", file=sys.stderr)
    print(f"  SPARQL endpoint: {NANOPUB_SPARQL_ENDPOINT_FULL}", file=sys.stderr)
    print(f"  depth limit = {args.depth}, max nodes = {args.max_nodes}",
          file=sys.stderr)

    nodes, edges, externals = walk(
        args.uri, depth_limit=args.depth, max_nodes=args.max_nodes,
        timeout=args.timeout, cache_dir=cache_dir,
    )

    write_constellation(nodes, edges, args.uri, externals,
                         out_dir / "constellation.json")

    if externals:
        (out_dir / "cited_papers.txt").write_text(
            "\n".join(sorted(externals)) + "\n"
        )

    print(file=sys.stderr)
    print(f"Imported {len(nodes)} nanopubs, {len(edges)} edges.", file=sys.stderr)
    print(f"  constellation: {out_dir / 'constellation.json'}", file=sys.stderr)
    print(f"  TriG cache:    {cache_dir}/", file=sys.stderr)
    if externals:
        print(f"  external DOIs: {out_dir / 'cited_papers.txt'} "
              f"({len(externals)} unique)", file=sys.stderr)

    by_type: dict[str, int] = {}
    for n in nodes.values():
        key = n.step_type or "<no template label>"
        by_type[key] = by_type.get(key, 0) + 1
    print(file=sys.stderr)
    print("Step-type breakdown:", file=sys.stderr)
    for t, c in sorted(by_type.items(), key=lambda kv: -kv[1]):
        print(f"  {c:3d} × {t}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
