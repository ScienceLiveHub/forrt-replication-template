# 08 — Research Synthesis (optional)

> Run the pre-flight checklist in `docs/forrt-form-fields.md` § Pre-flight checklist before drafting.
>
> Use this template only when this chain is **one of several** testing facets of a shared underlying property. The Synthesis names the cross-cutting conclusion and lists the multiple Outcomes as supporting sources.

**Form heading:** *"Science Live Research Synthesis — Synthesise findings across multiple replication outcomes with conclusions, recommendations, conditions, and limitations."*

## Fields

<!-- FIELDS:GENERATED step=08_synthesis — generated from nanopubs/templates/fields.snapshot.json; do not edit between the markers; regenerate with `pixi run -e tests gen-drafts` -->
**Template:** Science Live Research Synthesis  
**Template URI:** https://w3id.org/np/RApmrqOEr4f5bJC2vayrTnzhwnuEfAU_I4Pdg8K5JxeBw  
*9 fields, in form order. This block is generated from `nanopubs/templates/fields.snapshot.json`; edit guidance outside the markers, not here.*

### 1. short URI suffix for outcome ID

*URI · required*

```

```

### 2. label

*text · required*

```

```

### 3. Conclusion of the synthesis

*text (long) · required*

```

```

### 4. Recommendations

*text (long) · required*

```

```

### 5. Conditions of the synthesis

*text (long) · required*

```

```

### 6. Limitations of the synthesis

*text (long) · required*

```

```

### 7. URI of the source supporting the synthesis

*URI · required · repeatable*

```

```

### 8. 

*text · required*

```

```

### 9. topic

*search / select · required · repeatable*

_Search / select in the UI; type to filter._

```

```
<!-- /FIELDS:GENERATED -->

## Field notes

Guidance the template can't carry.

- **Short URI suffix / label** — the suffix becomes part of the nanopub URI (kebab-case slug); the label is a one-line summary.
- **conclusion / recommendations / conditions / limitations** — the aggregate finding across the underlying outcomes; actionable practitioner guidance; the scope it applies under (data types, methods, domains, regions, time periods); and what was not tested / might not generalise.
- **completion date** — default `{{RELEASE_DATE}}`.
- **supporting sources** — a **repeatable** group, ≥1 required. Each entry is a URL, typically the FORRT Outcome URIs being synthesised (this chain's Outcome, sibling-chain Outcomes, and a Research Software nanopub if applicable). Pull from `nanopubs/PUBLISHED.md` and/or sibling-repo registries.
- **topic** (Wikidata) — provide labels (not QIDs).

## Publication note

After publishing, paste the resulting URI into `nanopubs/PUBLISHED.md` step 08.
