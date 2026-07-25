# The reader-facing story page (`pixi run build-story`)

Once the FORRT chain is published (Phase 5) the science exists as a set of signed
nanopublications — precise, machine-actionable, but not something you would send a
colleague to *read*. `scripts/build_story.py` turns the published chain into a
**self-contained HTML article** that reads like a short blog post, while every value
on the page is taken verbatim from the signed nanopubs.

It is the same idea as `build-chain-draft`: **deterministic, off Claude's tokens.**
You run one command, review the output, commit it, and publish it wherever the
repository already publishes.

## What it produces

- A single `blog/index.html` — no external requests: the display font is embedded and
  the headline figure is downscaled and base64-inlined, so the page renders identically
  offline, in a Zenodo archive, or on GitHub Pages.
- The layout is an **aggregation of what the Science Live platform already shows** for
  each nanopublication (same field sets, same labels, same citation rule), restyled and
  reordered into an article. Nothing is invented; absent fields are omitted, never
  filled in.
- It auto-detects the shape from the constellation:
  - a **single replication chain** → one story (question → what is being replicated →
    study → outcome → citations → references);
  - a **research synthesis** (several chains composed into one finding) → a
    replication-forward synthesis page: a "what is being replicated / drawn from" card,
    a bottom-line callout, one full-width section per replication limb (each with its
    figure and verdict), and a References & citations block grouped per limb.

## Running it

```bash
export SCIENCELIVE_API_KEY=...        # the key you publish chains with
pixi run build-story                  # apex read from nanopubs/PUBLISHED.md -> blog/index.html
```

`build-story` reads the chain **apex** from `nanopubs/PUBLISHED.md`: the Research
Synthesis (step 08) if it was published, otherwise the Replication Outcome (step 05).
Publish the chain first (Phase 5) so the ledger is filled.

Options:

```bash
python scripts/build_story.py <apex-uri>          # render a specific URI
python scripts/build_story.py -o docs/story.html  # write somewhere else
```

The endpoint defaults to production (`api.sciencelive4all.org`); set `SCIENCELIVE_API`
to override it (e.g. a dev constellation). The script prints the verdict(s) and warns
on stderr if no headline figure could be resolved from `figures/`.

## Where to publish it

| Target | Role |
|---|---|
| **GitHub Pages** (same channel as the Jupyter Book) | primary — free, static, no server. Commit `blog/` and let Pages serve it. |
| **Zenodo release** | permanence — include the HTML in the archived deposit. |
| Science Live `/np/story?uri=…` | the canonical *hosted* version (a platform feature) — this repo build is the offline mirror. |

The page carries the **Science Live palette itself** (`scripts/story_assets/base.css` —
navy / magenta / blue, the same tokens as `science-live.css`), so it looks like a
Science Live page on any host; it does not inherit the surrounding site's theme.

## What it needs in the repository

- `nanopubs/PUBLISHED.md` with the published URIs (Phase 5).
- A headline figure under `figures/` (see `figures/README.md`) — used as the hero /
  per-limb result image. Optional, but the page is stronger with one.
- `scripts/story_assets/base.css` — the committed stylesheet (do not edit per project).

Everything else (author + ORCID, verdict, confidence, CiTO relations, topics, keywords,
conclusions, the paper title) is resolved live from the signed nanopubs and the
identifiers they carry.
