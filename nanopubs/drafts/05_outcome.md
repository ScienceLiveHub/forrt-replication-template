# 05 — FORRT Replication Outcome

> Run the pre-flight checklist in `docs/forrt-form-fields.md` § Pre-flight checklist before drafting.
>
> **Verify the actual numerical results first** by reading `results/` and `notebooks/03_analysis.py`. Don't quote numbers from memory. See `docs/verify-before-drafting.md`.

**Form heading:** *"FORRT Replication Outcome — Declare a replication study outcome according to FORRT"*

## Fields

<!-- FIELDS:GENERATED step=05_outcome — generated from nanopubs/templates/fields.snapshot.json; do not edit between the markers; regenerate with `pixi run -e tests gen-drafts` -->
**Template:** Declaring a replication study outcome according to FORRT  
**Template URI:** https://w3id.org/np/RA2zljn0Nw9SadppOyxZoh-_Rxosslrq-vYG-p9SttnJE  
*10 fields, in form order. This block is generated from `nanopubs/templates/fields.snapshot.json`; edit guidance outside the markers, not here.*

### 1. short URI suffix for outcome ID

*URI · required*

```

```

### 2. plain-text label for the outcome

*text · required*

```

```

### 3. choose study

*search / select · required*

_Search / select in the UI; type to filter._

```

```

### 4. repository URL

*URL or DOI · required*

```

```

### 5. choose completion date

*text · required*

```

```

### 6. choose validation status

*choice · required*

- [ ] contradicted
- [ ] inconclusive
- [ ] not tested
- [ ] partially supported
- [ ] validated

### 7. describe the overall conclusion about the original claim

*text (long) · required*

```

```

### 8. describe the evidence that supports your conclusion

*text (long) · required*

```

```

### 9. choose confidence level

*choice · required*

- [ ] high - Strong evidence, mostly agrees with original
- [ ] low - Limited evidence, significant disagreement
- [ ] moderate - Adequate evidence, partial agreement
- [ ] very high - Extensive evidence, high agreement with original
- [ ] very low - Minimal evidence, major disagreement

### 10. describe what limits the conclusions of the study

*text (long) · optional*

```

```
<!-- /FIELDS:GENERATED -->

## Field notes

Guidance the template can't carry.

- **Short URI suffix / label** — the suffix becomes part of the nanopub URI (kebab-case slug); the label is a descriptive title.
- **replication study** — the URI of the Replication Study published in step 04. Pull from `nanopubs/PUBLISHED.md`.
- **repository URL** — use the Zenodo **version DOI** URL for the release the results came from. Default: `https://doi.org/{{ZENODO_VERSION_DOI}}`.
  > **Why not the bare repo URL, and not the concept DOI.** `https://github.com/ORG/REPO` names a *moving branch*; this Outcome asserts "this code produced this number" in a signed, immutable record, so a branch URL points at whatever `main` becomes years from now. A concept DOI has the same flaw — it resolves to the latest version. The version DOI pins the exact release. `docs/chain-decision-tree.md` § Anchor ranks the options: SWHID > Zenodo version DOI > repo URL > Wayback. Both DOIs and the SWHID are in `CITATION.cff` under `identifiers:`, recorded at release by `.github/workflows/release-identifiers.yml` — take the one described as *"Version DOI"*.
- **completion date** — default `{{RELEASE_DATE}}`.
- **validation status** → maps to the CiTO intention in step 06: **validated → `confirms`**, **partially supported → `qualifies`**, **contradicted → `disputes`**. `inconclusive` / `not tested` have no canonical CiTO mapping — use `discusses` or `cites` when no stronger claim is warranted.
- **confidence level** — signals how strong the evidence is, *independent* of validation status: a `contradicted` outcome can be `high` confidence when the evidence against the original is strong.
- **conclusion / evidence / limitations** — conclusion is the substantive interpretation (replication's number vs the paper's, sign + significance); evidence is the numerical results/test statistics/coefficients, read directly from `results/`; limitations are honest caveats — if the result is partial or contradicted, say so plainly.

## Publication note

After publishing, paste the resulting URI into `nanopubs/PUBLISHED.md` step 05.
