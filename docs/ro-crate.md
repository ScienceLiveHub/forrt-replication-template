# `docs/ro-crate.md` — RO-Crate packaging

`ro-crate-metadata.json` at the repo root makes the whole repository a **Research Object Crate** ([RO-Crate 1.2](https://www.researchobject.org/ro-crate/specification/1.2/)): a FAIR Digital Object that says what the replication is, which workflow produced which files from which data, under which community profile, and which signed nanopublications state what was claimed and how it held.

**The file is generated, never hand-edited.** `scripts/build_rocrate.py` rebuilds it from what the repository already records:

```bash
pixi run -e rocrate build-rocrate       # writes ro-crate-metadata.json
pixi run -e rocrate validate-rocrate    # RO-Crate 1.2, REQUIRED level
```

CI rebuilds and validates it after every pipeline run, and the release workflow rebuilds it right after recording the version DOI and SWHID, so the committed crate always describes the latest release. On the uninitialised template the script does nothing and the placeholder crate stays as it is.

## Where each part comes from

| In the crate | Source |
|---|---|
| Name, description, keywords, authors (ORCID, affiliation), licence, date | `CITATION.cff` (`codemeta.json` as fallback for the description) |
| `identifier` (version DOI), `sameAs` (concept DOI), `isBasedOn` (SWHID), `version` | `CITATION.cff` `identifiers`, written by `set_release_identifiers.py` |
| `mainEntity`: the `Snakefile` as `ComputationalWorkflow`, Snakemake version from `pixi.lock` | the repo |
| Notebooks, `pixi.toml`, `Dockerfile`, result tables, NetCDF results and figures (`hasPart`, referenced in place) | the repo; files over 20 MB stay in the Zenodo release |
| Input datasets (`hasPart`, remote files) | `CITATION.cff` references of type `dataset` / `database` |
| `citation` (the original paper and other cited work) | the other `CITATION.cff` references |
| `subjectOf`: the six signed FORRT nanopublications | `nanopubs/PUBLISHED.md` |
| Community FAIR Implementation Profile, funding, study area, CCA fields | `rocrate.json` (optional, below) |

## `rocrate.json` — what the repo cannot say about itself

Copy `rocrate.example.json` to `rocrate.json` and keep only the keys you need:

| Key | Use |
|---|---|
| `profiles` | Profiles the crate `conformsTo`, e.g. the community's FAIR Implementation Profile nanopub |
| `funding` | Grants, each with its funder's ROR id (also used for the ROHub deposit) |
| `place` | Study area name and bounding box `[west, south, east, north]` |
| `inputs` | Input datasets, when they are not in `CITATION.cff` references (replaces them) |
| `citations` | Cited work, when not in `CITATION.cff` references (replaces them) |
| `project` / `publisher` | Publisher of the crate (default: the first author) |
| `results_license` | A separate licence for `results/` and `figures/` (e.g. CC BY 4.0, code stays MIT) |
| `main_workflow` | A Galaxy `.ga` workflow that is the study's real workflow (the Snakefile then only orchestrates) |
| `include` | Replace the default file patterns |
| `cca` | Climate-change adaptation studies: the [CCA RO-Crate profile](https://w3id.org/cca-crate-profile/0.9) fields (`sensitivity`, `data_collector`, `source`, `nature`) |
| `rohub` | ROHub deposit settings, see `docs/rohub-deposit.md` |

The CCA profile's terms are added as prefixes only: its published JSON-LD context redefines core terms with `https://schema.org`, which would change their meaning ([FAIR2Adapt/cca-crate-profile#4](https://github.com/FAIR2Adapt/cca-crate-profile/issues/4)).

## Choices made for validity

- Cited software is typed `CreativeWork`, not `SoftwareSourceCode`: the validator reads a code URL as a local script and fails.
- A referenced input `Dataset` is listed in `hasPart`, as RO-Crate 1.2 requires.
- `ro-crate-metadata.json` itself is never listed as a part: ROHub reserves that name (see `docs/rohub-deposit.md`).

## Why RO-Crate alongside `CITATION.cff` / `codemeta.json` / FORRT?

| Artefact | Captures | Audience |
|---|---|---|
| `CITATION.cff` | how to cite the software | humans, citation tools (Zotero, Zenodo) |
| `codemeta.json` | software-specific structured metadata | Software Heritage, OpenAIRE |
| `ro-crate-metadata.json` | the *whole research object* (workflow + data + code + provenance) as a navigable graph | ROHub, WorkflowHub, FAIR-RDM platforms |
| FORRT nanopub chain | typed scientific provenance: what claim, tested how, what result | nanopub network, Science Live, Wikidata |

The crate is built from the other three, so it adds a view, not a fourth thing to keep in sync.

## References

- [RO-Crate 1.2 specification](https://www.researchobject.org/ro-crate/specification/1.2/)
- [ro-crate-py](https://github.com/ResearchObject/ro-crate-py) and [rocrate-validator](https://github.com/crs4/rocrate-validator)
- [Workflow RO-Crate](https://www.researchobject.org/workflow-ro-crate/)
