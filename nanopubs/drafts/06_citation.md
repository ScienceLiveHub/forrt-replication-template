# 06 — CiTO Citation

> Run the pre-flight checklist in `docs/forrt-form-fields.md` § Pre-flight checklist before drafting.

**Description:** *"Declare citations between papers or other works, using Citation Typing Ontology"*

## Fields

<!-- FIELDS:GENERATED step=06_citation — generated from nanopubs/templates/fields.snapshot.json; do not edit between the markers; regenerate with `pixi run -e tests gen-drafts` -->
**Template:** Declare citations with CiTO  
**Template URI:** https://w3id.org/np/RA43F9EoOuzF0xoNUnCMNyFsfIqlsuWDdPHCnN0wCdCAw  
*3 fields, in form order. This block is generated from `nanopubs/templates/fields.snapshot.json`; edit guidance outside the markers, not here.*

### 1. DOI (https://doi.org/10...) or other URL of the citing article

*URL or DOI · required*

```

```

### 2. select the citation type

*choice · required · repeatable*

Choose one of 43 values from the controlled vocabulary (see https://w3id.org/np/RAZt5kzfoJg2m4dMRdMm2SP6JeUDD_GMzSq9xyRPMgP5k). See the field notes below for the FORRT-relevant subset.

### 3. DOI (https://doi.org/10...) or other URL of the cited article

*URL or DOI · required · repeatable*

```

```
<!-- /FIELDS:GENERATED -->

## Field notes

Guidance the template can't carry.

- **citing creative work** — the URI of the Outcome published in step 05. Pull from `nanopubs/PUBLISHED.md`.
- **citation type** — the generated block lists the full CiTO vocabulary (40+ relations). For FORRT chains, choose from the Outcome's validation status:
  - validated → **`confirms`**
  - partially supported → **`qualifies`**
  - contradicted → **`disputes`**
  - question-rooted chains with no original paper to confirm/dispute → **`usesMethodIn`** or **`citesAsAuthority`** for the methodology paper(s).
  > `replicates` is NOT in the Science Live vocabulary (despite existing in upstream CiTO). When citing a notebook/tutorial that was directly reused, use **`credits`** instead.
- **cited work** — the citation relation + cited work is a **repeatable** group: citation 1 is the back-link to the original paper (default `https://doi.org/{{PAPER_DOI}}`); add more for methods papers, related replications, or upstream tools.

## Publication note

After publishing, paste the resulting URI into `nanopubs/PUBLISHED.md` step 06.

This completes the six-step FORRT chain. Optional next layers:

- **Research Software** (`drafts/07_research_software.md`) — if the repo *produces* a reusable software artefact.
- **Research Synthesis** (`drafts/08_synthesis.md`) — if this chain is one of several testing facets of a shared property.
