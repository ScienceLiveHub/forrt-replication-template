---
name: import-from-nanopub
description: Seed Phase 1 of a fresh replication from a published nanopub URI instead of (or alongside) a paper PDF. Fetches every reachable nanopub in the chain — CiTO Citation, Research Synthesis, all chain steps, all sibling chains — and produces `nanopubs/imported/CHAIN_SUMMARY.md` summarising what's already been tested by whom, with what scope/method, and with what Outcome. Use when the new replication extends, qualifies, or builds on existing FORRT chains on the network.
---

# /import-from-nanopub

You're seeding Phase 1 of this replication from a **published nanopub URI** instead of (or in addition to) a paper PDF. The typical entry point is a CiTO Citation or a Research Synthesis nanopub at the apex of an existing chain; from that one URI the whole constellation is reachable by traversing CiTO citations and provenance links.

This skill produces a structured summary that the `paper-analyst` agent (and the human running the replication) can read as if it were `00_paper_summary.md`, except it summarises **prior signed claims about the upstream paper**, not the paper itself.

## When to use this skill

- **Extending an existing chain.** Same upstream paper, new dataset / method / region. You want to see what's already been claimed so the new chain can `extends` prior work via CiTO instead of duplicating it.
- **Replacing or qualifying a contradicted chain.** Prior work disputed the upstream paper; you want to re-test under different conditions.
- **Awareness-check before fresh replication.** Same upstream paper; you want to confirm there is no near-duplicate already on the network.
- **Constellation entry point.** Given a Research Synthesis URI, you want to expand it back into its constituent Outcome / Study / Claim / AIDA / Quote chain steps.

## When NOT to use

- Your replication has no relationship to existing FORRT chains on the network — use the paper-rooted Phase 1 (`paper-analyst` agent on a PDF) instead.
- The entry URI is from outside the Science Live / nanopub network (a Wikidata item, a Zenodo DOI). The skill is nanopub-network-specific.

## Procedure

### Step 1 — Get the entry URI

Ask the user for the entry URI. Acceptable forms:

- `https://w3id.org/sciencelive/np/RA...` (Science Live)
- `https://w3id.org/np/RA...` (Nanodash / nanopub network)

Reject URIs that don't match this pattern with a helpful message — this skill is nanopub-network-specific.

### Step 2 — Verify the URI actually resolves

Before running the full crawl, sanity-check the entry URI exists. Open it in the Science Live viewer:

```
https://w3id.org/sciencelive/np/RA...  → opens the viewer with Template View / RDF View tabs
```

…or fetch its TriG:

```bash
curl -s -L -H "Accept: application/trig" "<URI>" | head -50
```

If the response is empty or 404, stop. Tell the user: *"That URI does not resolve. Common reasons: (1) typo in the URI, (2) the nanopub was retracted, (3) network issue. Verify in the Science Live viewer first."* See `feedback_nanopub_uri_verification.md` in the user's auto-memory — `PUBLISHED.md` files are not always exhaustive, but the viewer is authoritative.

### Step 3 — Run the importer script

```bash
python3 scripts/import-nanopub-chain.py <ENTRY-URI>
```

What this does:

- BFS-walks the citation + provenance graph from the entry URI, fetching every reachable nanopub (default depth 5, default cap 80 nodes — generous, almost any real constellation fits)
- Caches each fetched TriG to `nanopubs/imported/trig/<RA-id>.trig` so re-runs are fast
- Writes `nanopubs/imported/constellation.json` — structured graph: nodes (URI → step type → key fields) + edges (CiTO + provenance relations)
- Writes `nanopubs/imported/cited_papers.txt` — external (non-nanopub) URIs cited, typically the upstream paper DOI(s)

Network access is required. The script is dependency-light: stdlib + `rdflib`. If `rdflib` is missing, the script prints a clear error; install with `pip install rdflib` in the same env you run the other replication scripts in.

If the user has no network (e.g. air-gapped HPC), they should run this step on a different machine and copy the `nanopubs/imported/` directory across.

### Step 4 — Read constellation.json and the cached TriG

Open `nanopubs/imported/constellation.json` and inspect:

- `entry` — the URI the user gave you
- `node_count` / `edge_count` — sanity check (typical FORRT chain: 6–8 nodes single-chain; 18–25 multi-chain constellation)
- `nodes[]` — each fetched nanopub with `step_type`, `cito_relations`, `prov_derived_from`, `plain_text_excerpts` (heuristically-extracted human-readable strings)
- `edges[]` — CiTO and provenance relations between nodes
- `external_citations` — upstream paper DOIs

For each interesting node, also read the cached TriG at `node.raw_trig_path`. The script's heuristic `step_type` classification is good but not infallible; the cached TriG is the ground truth. Look at the Assertion graph for the substantive content (verbatim Quote text, AIDA sentence, Claim type + statement, Outcome verdict, etc.).

### Step 5 — Generate `CHAIN_SUMMARY.md`

Write `nanopubs/imported/CHAIN_SUMMARY.md`. Structure it as the *prior-work analogue* of `nanopubs/drafts/00_paper_summary.md`:

```markdown
# Prior FORRT chain summary

**Entry URI**: <entry_uri>
**Imported on**: <ISO date>
**Constellation size**: <N> unique nanopubs across <K> chain(s)

## Upstream paper

<DOI(s) and resolved title — extract title from TriG dct:title if present;
otherwise leave for the user to fill in. Cite the paper DOI verbatim.>

## Chain(s) already published

For each chain found in the constellation:

### Chain <ID> — <short label, derived from authors/Study text>

| Step | Template | URI | Key content |
|---|---|---|---|
| 01 | Quote-with-comment | RA... | "<verbatim Quote text>" |
| 02 | AIDA | RA... | "<AIDA sentence>" |
| 03 | FORRT Claim | RA... | type=<claim type>, statement="..." |
| 04 | FORRT Replication Study | RA... | scope="...", method="..." |
| 05 | FORRT Replication Outcome | RA... | verdict=<Validated/PartiallySupported/Contradicted>, "..." |
| 06 | CiTO Citation | RA... | cito:<relation> → <upstream paper DOI> |
| 07 | Research Software | RA... | <if present> |

Authors (ORCIDs): <list>

### Apex Research Synthesis (if present)

URI: RA...
Aggregates: <chain-IDs>
Synthesis verdict: "..."

### Synthesis-level CiTO (if present)

URI: RA...
Relation: cito:<relation> → upstream paper DOI
Statement: "..."

## What this new replication can do

Given prior chains, the new replication's natural positioning:

- If a prior chain `confirms` and the new replication tests a different
  taxon / region / horizon → new chain's CiTO will `extends` prior chain
  via CiTO `cito:extends` to one of prior CiTO URIs.
- If a prior chain `qualifies` and the new replication might either
  reinforce or contradict the qualifying finding → new CiTO is either
  `cito:confirms` (qualifies the qualification — note this in the CiTO
  "personal comment" field) or `cito:disputes`.
- If no prior chain exists for the dimension the new replication tests →
  fresh sibling chain, CiTO relation as appropriate to the new Outcome
  verdict (`confirms` / `qualifies` / `disputes` / `extends` upstream paper).

## Methodological precedents to inherit

- Scope and method definitions in prior Replication Study nanopubs — read
  these before drafting `nanopubs/drafts/04_study.md` to ensure
  comparability where intended.
- Limitation declarations in prior Replication Outcome nanopubs — these
  flag deviations the prior authors had to make; your replication may
  hit the same constraints.

## Open questions for the user

<List 3-5 specific questions about how the new replication should position
relative to the prior constellation. These typically include:>

- Will the new replication `extends` the canonical chain's CiTO, or open
  a fresh chain rooted on the upstream paper?
- Are there prior Research Software nanopubs whose toolchain we should
  reuse (mark as cited via CiTO `cito:usesMethodIn`)?
- Does the prior Synthesis already cover the case we're testing? If so,
  do we add a new chain or extend the existing Synthesis?
```

Keep the summary **factual and short**. Do not editorialise. The user (and
the `paper-analyst` agent that runs next) will read this to position the new
replication.

### Step 6 — Hand off to Phase 1

After `CHAIN_SUMMARY.md` is written, tell the user:

> *"Imported `<N>` nanopubs from the constellation rooted at `<entry-URI>`. Summary at `nanopubs/imported/CHAIN_SUMMARY.md`. Open questions are listed at the bottom — answer those before drafting any nanopubs. Then either: (a) place the upstream paper PDF at `paper/<name>.pdf` and run the `paper-analyst` agent in Phase 1 with `CHAIN_SUMMARY.md` as the prior-work context, or (b) skip directly to Phase 2 if the new replication is a pure method-extension of a prior chain and doesn't need fresh paper analysis."*

## Failure modes

- **Empty constellation (0 nodes fetched)** — entry URI didn't resolve, or the BFS hit a non-Science-Live URI immediately. Re-verify the entry URI via Step 2.
- **Crawl hits the node cap (≥ max-nodes)** — the constellation is larger than expected; either bump `--max-nodes 200` or narrow the entry URI to a more specific point in the chain.
- **All `step_type = "Unknown"`** — the template-URI heuristics in the script didn't match. Read the TriG manually and infer step types; if a new template family is being used, extend `STEP_TYPE_HINTS` in `scripts/import-nanopub-chain.py`.
- **Verbatim text excerpts are short / cryptic** — the heuristic `extract_plain_text` returns the longest literals first, but for some nanopubs the substantive content is in `rdfs:label` of nested entities. Open the cached TriG and read manually.
- **Cycle in the citation graph** — the BFS uses a `visited` set so cycles are not a hazard, but `prov:wasDerivedFrom` chains can be long; if the BFS feels slow, lower `--depth`.

## Companion docs

- `docs/nanopub-chain-discovery.md` — when this entry point makes sense vs. a paper-rooted Phase 1.
- `docs/forrt-form-fields.md` — the form structure of each FORRT chain step.
- `docs/chain-decision-tree.md` — which template starts a chain; paper-rooted vs question-rooted.
- `docs/programmatic-nanopubs.md` — for batch / retract / supersede operations.
- `/verify-chain` skill — once the new replication has its own chain published, run that skill to check internal+external consistency.
