# 04 — FORRT Replication Study

> Run the pre-flight checklist in `docs/forrt-form-fields.md` § Pre-flight checklist before drafting.
>
> **Verify code first:** read the actual reproduction script in `notebooks/03_analysis.py` before writing the methodology field. See `docs/verify-before-drafting.md`.

**Form heading:** *"FORRT Replication — Declare a replication study design according to FORRT"*

## Fields

<!-- FIELDS:GENERATED step=04_study — generated from nanopubs/templates/fields.snapshot.json; do not edit between the markers; regenerate with `pixi run -e tests gen-drafts` -->
**Template:** Declaring a replication study design according to FORRT  
**Template URI:** https://w3id.org/np/RAuLEjPp-4dTvPwMkfHggTto1CgjIftiGRAgHlyeEonjQ  
*9 fields, in form order. This block is generated from `nanopubs/templates/fields.snapshot.json`; edit guidance outside the markers, not here.*

### 1. short URI suffix for study ID

*URI · required*

```

```

### 2. label/name of replication study

*text · required*

```

```

### 3. choose the study type

*choice · required*

- [ ] Replication Study - replication with different methodology or conditions
- [ ] Reproduction/Replication Study - study that is both, reproduction and replication
- [ ] Reproduction Study - direct reproduction: same methodology, same tools

### 4. choose FORRT claim

*search / select · required*

_Search / select in the UI; type to filter._

```

```

### 5. Describe what part of the claim is reproduced/replicated.

*text (long) · required*

```

```

### 6. Describe how the claim is reproduced/replicated.

*text (long) · required*

```

```

### 7. Describe any deviations from original methodology.

*text (long) · optional*

```

```

### 8. choose terms as related keywords

*search / select · optional · repeatable*

_Search / select in the UI; type to filter._

```

```

### 9. Choose the scientific discipline

*search / select · optional*

_Search / select in the UI; type to filter._

```

```
<!-- /FIELDS:GENERATED -->

## Field notes

Guidance the template can't carry.

- **Short URI suffix / label** — the suffix becomes part of the nanopub URI (kebab-case slug); the label is the human-readable title.
- **FORRT claim** — the URI of the Claim published in step 03. Pull from `nanopubs/PUBLISHED.md`.
- **scope** (*what part of the claim is reproduced/replicated*) — which aspect, what's in/out of scope. This is **scope, not methodology and not results**. See `docs/pico-study-outcome-levels.md`.
- **methodology** (*how the claim is reproduced/replicated*) — the method in plain prose. **Read `notebooks/03_analysis.py` and any config first**; don't extrapolate framework or hyperparameters. Not exact numerical results.
- **deviations** — what differs from the original method; verify against the actual code, don't guess.
- **keywords / discipline** (Wikidata) — provide labels (not QIDs); the Wikidata search picks up labels.

## Publication note

After publishing, paste the resulting URI into `nanopubs/PUBLISHED.md` step 04.
