# 01 — PICO Research Question (question-rooted chains, comparative)

> Use this draft instead of `01_quote.md` if your chain is question-rooted with a clear comparator (X vs Y). For descriptive/scoping question-rooted chains, use `01_pcc.md`. See `docs/chain-decision-tree.md`.
>
> Run the pre-flight checklist in `docs/forrt-form-fields.md` § Pre-flight checklist before drafting.
>
> **After choosing the chain shape, delete the two step-1 alternates you aren't using.** Once you've decided this chain is question-rooted-comparative and keep `01_pico.md`, run:
> ```bash
> rm nanopubs/drafts/01_quote.md nanopubs/drafts/01_pcc.md
> ```

**Form heading:** *"PICO Research Question — Define a research question using the PICO framework (Population, Intervention, Comparator, Outcome)"*

## Fields

<!-- FIELDS:GENERATED step=01_pico — generated from nanopubs/templates/fields.snapshot.json; do not edit between the markers; regenerate with `pixi run -e tests gen-drafts` -->
**Template:** Defining a PICO-based research question  
**Template URI:** https://w3id.org/np/RA5e5XeXy_-aNK5giB7kBAEQslTLVydHeM4YYEzhmEE2w  
*8 fields, in form order. This block is generated from `nanopubs/templates/fields.snapshot.json`; edit guidance outside the markers, not here.*

### 1. short ID used as URI suffix

*URI · required*

```

```

### 2. label for the research question

*text · required*

```

```

### 3. description of the research question

*text (long) · required*

```

```

### 4. choose the type of research question

*choice · required*

- [ ] causation research question - (Does factor X cause outcome Y?)
- [ ] descriptive research question - (What are the characteristics of X?)
- [ ] effectiveness research question - (Does approach X work better than Y?)
- [ ] experience research question - (How do people experience phenomenon X?)
- [ ] prediction research question - (What outcomes can we expect from X?)

### 5. description of the population

*text (long) · required*

```

```

### 6. description of the intervention group

*text (long) · required*

```

```

### 7. description of the comparator group

*text (long) · required*

```

```

### 8. description of the outcome group

*text (long) · required*

```

```
<!-- /FIELDS:GENERATED -->

## Field notes

Guidance the template can't carry.

- PICO is the **question**, stated at discipline level. Keep implementation specifics (grid resolution, library, model class) out of every field — those belong in the Replication Study's *how* field. See `docs/pico-study-outcome-levels.md`.
- **Population / Intervention / Comparison / Outcome** — each is a discipline-level concept: who/what is studied, the intervention or exposure, the comparison or control condition, and the *kind* of outcome measured (not the value).
- Short-ID fields become part of the nanopub URI — use a kebab-case slug.

## Publication note

After publishing, paste the resulting URI into `nanopubs/PUBLISHED.md` step 01.
