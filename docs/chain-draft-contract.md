# `chain-draft.json` — the pre-filled FORRT-chain hand-off contract

This document defines `chain-draft.json`: the interface between **this template
repo** (which produces it) and the **Science Live platform's FORRT-chain wizard**
(which consumes it). It exists so a user can publish a whole FORRT chain by
reviewing pre-filled fields step by step, instead of hand-copying values from the
`nanopubs/drafts/` files into the Science Live form and pasting URIs back into
`PUBLISHED.md`.

## The workflow it enables

Today: the drafts are authored during the replication; the user then reads each
one, **manually** fills the fields in `platform.sciencelive4all.org`, publishes,
copies the returned URI back into `nanopubs/PUBLISHED.md`, and repeats — six
times, in order. At the end `PUBLISHED.md` becomes the Jupyter Book landing page.

With this contract: the template repo emits one `chain-draft.json` carrying every
step's values. The platform wizard imports it and walks the user through the
chain — each step pre-filled, the user reviews and publishes, and **the wizard
carries each published URI into the next step's back-reference automatically**
(no copy-paste). The URI ledger falls out of the wizard rather than being
hand-maintained.

Two things pre-fill each step:

1. **Repo-derived values** — carried in this file (`prefill`). Only the repo
   knows these: the paper DOI, the Zenodo version DOI, the SWHID, the release
   date, and the drafted content (quotation, methodology, conclusion, …).
2. **Chain linkage** — *not* in this file. Step N's published URI fills step
   N+1's back-reference field; the wizard owns this because only it knows the URI
   at publish time. This file only declares the topology (`carry_forward`).

## Producer and consumer

- **Producer:** `scripts/build_chain_draft.py` in this repo (reads `CITATION.cff`,
  `nanopubs/PUBLISHED.md`, `nanopubs/drafts/`, and `nanopubs/templates/` — see
  "Value sources"). Output: `nanopubs/chain-draft.json` (git-ignored; regenerable).
- **Consumer:** the platform wizard (`science-live-platform`), which already has
  every FORRT template form component and a dormant `prefilledData` prop on each.
  The wizard maps each step's `prefill` object onto that prop.

## Field-name keys are the platform's, not ours

The keys inside `prefill` are the **exact field `name`s of the platform's template
components** (what its `prefilledData` prop expects) — verified against
`science-live-platform/frontend/src/pages/np/create/components/templates/`. They
happen to equal the placeholder local names in `nanopubs/templates/fields.snapshot.json`,
but the platform component is the authority. If a template component renames a
field, this contract's keys follow it (and `build_chain_draft.py` must be updated).

| Step (`step`) | `template_key` | Field keys (component `name`s) |
|---|---|---|
| `01_quote` | `ANNOTATE_QUOTATION` | `paper`, `quotation`, `quotation-end`, `comment` |
| `02_aida` | `AIDA_SENTENCE` | `aida`, `topic`, `project`, `dataset`, `publication` |
| `03_claim` | `FORRT_CLAIM` | `claim`, `label`, `aida`, `forrtType`, `source` |
| `04_study` | `FORRT_REPLICATION` | `study`, `label`, `type`, `claim`, `scope`, `methodology`, `deviation` |
| `05_outcome` | `FORRT_REPLICATION_OUTCOME` | `outcome`, `label`, `study`, `repo`, `date`, `validationStatus`, `confidenceLevel`, `conclusion`, `evidence`, `limitations` |
| `06_citation` | `CITATION_CITO` | `work`, `cites`, `cited` |

Question-rooted chains replace `01_quote` with `01_pico` (`PICO_RESEARCH_QUESTION`)
or `01_pcc` (`PCC_RESEARCH_QUESTION`); the optional `07_research_software`
(`RESEARCH_SOFTWARE`) and `08_synthesis` (`RESEARCH_SYNTHESIS`) steps append when
applicable.

## Carry-forward topology

Each step's published URI fills one field of the next step. These edges are fixed
for a FORRT chain and are declared in `carry_forward` so the wizard is generic:

| From (published) | Into | Field |
|---|---|---|
| `01_quote` | `02_aida` | `project` (labelled "Relates to this nanopublication") |
| `02_aida` | `03_claim` | `aida` |
| `03_claim` | `04_study` | `claim` |
| `04_study` | `05_outcome` | `study` |
| `05_outcome` | `06_citation` | `work` |

The wizard fills the carry-forward field from its captured URI; it does **not**
appear in the producer's `prefill` (the URI does not exist until publish time).

### Known friction (for the wizard implementer)

Most back-reference fields are plain text inputs (`02_aida.project`,
`06_citation.work`) and prefill cleanly. But `04_study.claim` is a custom search
combobox (`QueryComboboxField`) with its own internal selection state — setting
the form value may not update its visible selection. The wizard should set the
widget's display state as well as the form value for combobox-backed carry-forward
fields.

## Schema

```jsonc
{
  "schema_version": "1.0",
  "kind": "forrt-chain-draft",
  "chain_shape": "paper-rooted",          // "paper-rooted" | "pico" | "pcc"
  "source": {
    "repository": "https://github.com/OWNER/REPO",
    "commit": "<sha>"                      // the repo state the values were drawn from
  },
  "steps": [
    {
      "step": "01_quote",                  // stable step id (matches nanopubs/drafts/ + snapshot)
      "template_key": "ANNOTATE_QUOTATION",
      "template_uri": "https://w3id.org/np/RA24onqmqTMsraJ7ypYFOuckmNWpo4Zv5gsLqhXt7xYPU",
      "prefill": {                         // component field name -> value; only known values appear
        "paper": "10.5281/zenodo.123456",
        "quotation": "…verbatim…",
        "comment": "…interpretation…"
      },
      "provenance": {                      // optional: where each value came from, for the review UI
        "paper": "CITATION.cff references[article]",
        "quotation": "nanopubs/drafts/01_quote.md",
        "comment": "nanopubs/drafts/01_quote.md"
      },
      "manual": ["quoteType"],             // optional: fields the user must set/choose in the wizard
      "published_uri": null                // from PUBLISHED.md; non-null means already done (resume)
    }
  ],
  "carry_forward": [
    { "from": "01_quote",   "into": "02_aida",     "field": "project" },
    { "from": "02_aida",    "into": "03_claim",    "field": "aida"    },
    { "from": "03_claim",   "into": "04_study",    "field": "claim"   },
    { "from": "04_study",   "into": "05_outcome",  "field": "study"   },
    { "from": "05_outcome", "into": "06_citation", "field": "work"    }
  ]
}
```

Rules:

- **Only known values appear in `prefill`.** A field the repo can't fill is
  simply absent — the wizard renders it empty for the user. Never emit a `{{TOKEN}}`
  or a placeholder string as a value.
- **`manual`** lists fields the user is expected to decide in the wizard — the
  judgment calls (`forrtType`, `validationStatus`, `confidenceLevel`, `type`, the
  CiTO `cites` relation). The wizard already renders these with the template's own
  vocabulary; `manual` is a review-UI hint, not data.
- **`published_uri`** lets the wizard resume a partly-published chain: skip steps
  that already have a URI and seed carry-forward from them.
- **Determinism:** the producer does not stamp a timestamp (so regenerating on an
  unchanged repo yields an identical file); `source.commit` records the state.

## Value sources (what the producer fills from where)

| Field(s) | Source |
|---|---|
| `01_quote.paper`, `03_claim.source`, `06_citation.cited` (paper DOI) | `CITATION.cff` → `references` (`type: article`) → `doi` |
| `05_outcome.repo`, `07_research_software.software` (version DOI) | `CITATION.cff` → `identifiers` → the **Version DOI** entry |
| `07_research_software` SWHID | `CITATION.cff` → `identifiers` (`type: swh`) |
| `05_outcome.date`, `08_synthesis` date | `CITATION.cff` → `date-released` |
| `*.label` | derived from `CITATION.cff` `title` / the drafted content |
| `quotation`, `comment`, `aida`, `scope`, `methodology`, `deviation`, `conclusion`, `evidence`, `limitations`, … (drafted content) | `nanopubs/drafts/0X_*.md` (authored by the `nanopub-drafter` agent during the replication) |
| `carry_forward` fields, `published_uri` | `nanopubs/PUBLISHED.md` |
| field set, `template_uri`, dropdown vocabularies | `nanopubs/templates/registry.json` + `fields.snapshot.json` |

Identity (author ORCID/name) is **not** a chain-draft field — the platform takes
it from the signed-in user's profile.

## Versioning

`schema_version` is bumped on any breaking change to the shape. The wizard should
reject a `schema_version` it doesn't understand rather than guess. Additive,
optional fields (like `provenance`) do not bump the major version.
