# 03 — FORRT Claim

> Run the pre-flight checklist in `docs/forrt-form-fields.md` § Pre-flight checklist before drafting.

**Form heading:** *"FORRT Claim — Declare an original claim according to FORRT, linking it to an AIDA sentence with a specific FORRT type."*

## Fields

<!-- FIELDS:GENERATED step=03_claim — generated from nanopubs/templates/fields.snapshot.json; do not edit between the markers; regenerate with `pixi run -e tests gen-drafts` -->
**Template:** Declaring an original claim according to FORRT  
**Template URI:** https://w3id.org/np/RAZWyM8D16ya3S1zhCvrG1f0iSpd9-8onVWp0FTvvX7LQ  
*5 fields, in form order. This block is generated from `nanopubs/templates/fields.snapshot.json`; edit guidance outside the markers, not here.*

### 1. Short URI suffix as claim ID

*URI · required*

```

```

### 2. label of the claim, to find it later

*text · required*

```

```

### 3. choose AIDA sentence of claim

*search / select · required*

_Search / select in the UI; type to filter._

```

```

### 4. Type of FORRT claim

*choice · required*

- [ ] computational performance (Computational & Performance)
- [ ] data governance (access control, licensing, FAIR compliance)
- [ ] data quality (preprocessing, validation, normalization)
- [ ] descriptive pattern (distribution, trend, proportion)
- [ ] model performance (accuracy, F1 score, evaluation metrics)
- [ ] scalability (Computational & Performance)
- [ ] statistical significance (significant difference, relationship, or effect)

### 5. source URI

*URL or DOI · optional*

```

```
<!-- /FIELDS:GENERATED -->

## Field notes

Guidance the template can't carry.

- **Short URI suffix / label** — the suffix becomes part of the nanopub URI (kebab-case slug); the label is a descriptive title, not a sentence, used for search/discovery.
- **AIDA sentence** — the URI of the AIDA published in step 02. Pull from `nanopubs/PUBLISHED.md`. If it was published via Nanodash (`w3id.org/np/…` namespace), the platform search may not find it — paste the URI manually.
- **Type of FORRT claim** — pick exactly one of the seven. See `docs/claim-type-vocabulary.md` for what each means and how to choose.
- **Source URI** (optional) — the original paper, in full `https://doi.org/…` form (**not** the bare DOI). Default: `https://doi.org/{{PAPER_DOI}}`.

## Publication note

After publishing, paste the resulting URI into `nanopubs/PUBLISHED.md` step 03.
