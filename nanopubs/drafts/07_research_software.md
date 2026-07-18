# 07 — Research Software (optional)

> Run the pre-flight checklist in `docs/forrt-form-fields.md` § Pre-flight checklist before drafting.
>
> **Scope check:** Research Software nanopubs describe **reusable software artefacts** — tools people would `pip install` or `git clone` to use in their own work. They do NOT describe one-off demo / reproduction repos. If your repo is a reproduction of someone else's paper, the reusable artefact is the *upstream library* it uses (e.g. `foscat`, `planktonclas`), not your reproduction repo. Author the Research Software nanopub for the upstream tool, not the demo. See `CLAUDE.md` § Layered architecture: FORRT vs Research Software.

**Form heading:** *"Research Software — Describe research software with metadata including repository, supporting publications, and related resources."*

## Fields

<!-- FIELDS:GENERATED step=07_research_software — generated from nanopubs/templates/fields.snapshot.json; do not edit between the markers; regenerate with `pixi run -e tests gen-drafts` -->
**Template:** Describing research software at summary level - simple  
**Template URI:** https://w3id.org/np/RABBzVTxosLGT4YBCfdfNd6LyuOOTe2EVOTtWJMyOoZHk  
*7 fields, in form order. This block is generated from `nanopubs/templates/fields.snapshot.json`; edit guidance outside the markers, not here.*

### 1. URI of published software

*URI · required*

```

```

### 2. title of published software

*text · required*

```

```

### 3. URI of repository where software is published

*URI · required*

```

```

### 4. URI of nanopublication for research project that produced software

*search / select · required*

_Search / select in the UI; type to filter._

```

```

### 5. URI of related scholarly work (e.g. publication)

*URI · optional · repeatable*

```

```

### 6. URI of license of published software

*URI · optional*

```

```

### 7. URI of published dataset

*URI · optional · repeatable*

```

```
<!-- /FIELDS:GENERATED -->

## Field notes

Guidance the template can't carry.

- **URI of published software** — use the Zenodo **version DOI** URL (`https://doi.org/10.5281/zenodo.<N>` for the specific release), NOT the concept DOI. Default: `https://doi.org/{{ZENODO_VERSION_DOI}}`. Fall back to a GitHub URL only if there is no Zenodo deposit at all.
  > **Why the version DOI, not the concept DOI.** A concept DOI resolves to whatever version is *latest*. This nanopub is signed and immutable — once published it can only be retracted or superseded, never edited. If it names a concept DOI, the moment a v0.2.0 is released this permanent record silently starts describing different code, with no signature breakage and nothing to alert a reader. Both DOIs are in `CITATION.cff` under `identifiers:` (recorded at release by `.github/workflows/release-identifiers.yml`); take the one described as *"Version DOI"*. The concept DOI is correct in `CITATION.cff`'s top-level `doi:` field ("cite this project") and wrong here.
- **Software Heritage ID** (there is no dedicated template field — record it via a Related resource / the repository note) — the SWHID from `CITATION.cff` `identifiers:` (`type: swh`). It pins the exact source tree in a preservation archive, so it still resolves if the repo is deleted, renamed, or force-pushed. `docs/chain-decision-tree.md` ranks it above the Zenodo DOI. Default: `{{SWHID}}`.
- **repository URL** — default `https://github.com/{{REPO_ORG}}/{{REPO_NAME}}`.
- **research project** — the URI of the FORRT Claim or PCC question this software is associated with (the back-link to the chain). Pull from `nanopubs/PUBLISHED.md`.
- **license** — e.g. `https://spdx.org/licenses/MIT.html`.
- **datasets / research output** — input data DOIs (Zenodo data records, ESA product DOIs); the research-output back-link is the FORRT Outcome URI(s) the software implements, plus any cited methods papers.

## Publication note

After publishing, paste the resulting URI into `nanopubs/PUBLISHED.md` step 07.
