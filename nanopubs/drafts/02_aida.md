# 02 — AIDA Sentence

> Run the pre-flight checklist in `docs/forrt-form-fields.md` § Pre-flight checklist before drafting.

**Form heading:** *"AIDA Sentence — Make structured scientific claims following the AIDA model"*

## Fields

<!-- FIELDS:GENERATED step=02_aida — generated from nanopubs/templates/fields.snapshot.json; do not edit between the markers; regenerate with `pixi run -e tests gen-drafts` -->
**Template:** Expressing a statement about research as an AIDA sentence  
**Template URI:** https://w3id.org/np/RALmXhDw3rHcMveTgbv8VtWxijUHwnSqhCmtJFIPKWVaA  
*5 fields, in form order. This block is generated from `nanopubs/templates/fields.snapshot.json`; edit guidance outside the markers, not here.*

### 1. Type your AIDA sentence here (ending with a full stop)

*URI · required · max 500 chars · prefix `http://purl.org/aida/`*

```

```

### 2. URI of concept or topic the sentence is about

*search / select · optional · repeatable*

_Search / select in the UI; type to filter._

```

```

### 3. URI of nanopublication for related research project

*search / select · required*

_Search / select in the UI; type to filter._

```

```

### 4. URI of related published dataset

*URI · optional · repeatable*

```

```

### 5. URI of related scholarly work (e.g. publication)

*URI · optional · repeatable*

```

```
<!-- /FIELDS:GENERATED -->

## Field notes

Guidance the template can't carry.

- **The AIDA sentence** — Atomic, Independent, Declarative, Absolute. One empirical finding, ending with a full stop. If your draft contains "and" linking two distinct findings, split it into two AIDA nanopubs anchored on two separate Claims. State what is true *in the world*, not what the model/test found — see the AIDA pre-write checklist in `.claude/agents/nanopub-drafter.md`.
- **URI of nanopublication for related research project** — for FORRT chains this is the back-link: the Quote-with-comment URI (paper-rooted) or the PICO/PCC URI (question-rooted), from step 01. Pull it from `nanopubs/PUBLISHED.md`.
- **Supported by datasets / other publications** — DOIs/URLs grounding the claim (datasets; peer-reviewed methods papers, or the original paper if not cited via the Quote).
- **Known platform bug (2026-04-26):** if both *dataset* and *publication* support groups are populated and publishing fails, publish this AIDA via Nanodash instead. Its URI namespace becomes `https://w3id.org/np/…` (still valid and citable); record the namespace in `PUBLISHED.md`.

## Publication note

After publishing, paste the resulting URI into `nanopubs/PUBLISHED.md` step 02.
