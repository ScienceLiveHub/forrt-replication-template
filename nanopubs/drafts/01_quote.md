# 01 — Quote-with-comment (paper-rooted chains)

> Run the pre-flight checklist in `docs/forrt-form-fields.md` § Pre-flight checklist before drafting.
>
> If this is a question-rooted chain, use `01_pico.md` or `01_pcc.md` instead — see `docs/chain-decision-tree.md`.
>
> **After choosing the chain shape, delete the two step-1 alternates you aren't using.** Once you've decided this chain is paper-rooted and keep `01_quote.md`, run:
> ```bash
> rm nanopubs/drafts/01_pico.md nanopubs/drafts/01_pcc.md
> ```

**Form heading:** *"Annotate a paper quotation — Annotating a paper quotation with personal interpretation"*

## Fields

<!-- FIELDS:GENERATED step=01_quote — generated from nanopubs/templates/fields.snapshot.json; do not edit between the markers; regenerate with `pixi run -e tests gen-drafts` -->
**Template:** Annotating a paper quotation with personal interpretation  
**Template URI:** https://w3id.org/np/RA24onqmqTMsraJ7ypYFOuckmNWpo4Zv5gsLqhXt7xYPU  
*4 fields, in form order. This block is generated from `nanopubs/templates/fields.snapshot.json`; edit guidance outside the markers, not here.*

### 1. DOI of the paper (starting with '10.')

*URI · required · prefix `https://doi.org/`*

```

```

### 2. The exact quotation from the paper (max. 500 characters)

*text (long) · required · max 500 chars*

```

```

### 3. End of quotation (optional - use when quoting beginning and end of a longer passage, max. 500 characters)

*text (long) · optional · max 500 chars*

```

```

### 4. our interpretation and explanation of why this quotation is relevant (max. 800 characters)

*text (long) · required · max 800 chars*

```

```
<!-- /FIELDS:GENERATED -->

## Field notes

Guidance the template can't carry. Fields are named as above.

- **DOI of the paper** — enter the bare DOI starting with `10.`, **not** the `https://doi.org/…` form (the template adds the prefix itself). Default: `{{PAPER_DOI}}`.
- **The exact quotation** — verbatim from the paper PDF in `paper/`, character-for-character. **Read the PDF first; don't paraphrase from memory** (`docs/verify-before-drafting.md`). Hard cap 500 chars; if the passage is longer, use *End of quotation* to mark a start+end span instead of pasting the whole thing.
- **Our interpretation…** — why this quote matters and what the replication tests; connect the paper's claim to the work this repo does. Don't repeat the quote. Hard cap 800 chars, but aim well under it.

## Publication note

After publishing, paste the resulting URI into `nanopubs/PUBLISHED.md` step 01.
