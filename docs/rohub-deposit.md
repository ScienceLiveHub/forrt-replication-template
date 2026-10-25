# `docs/rohub-deposit.md` — Depositing as a ROHub Research Object

[ROHub](https://www.rohub.org) hosts citable Research Objects (w3id PIDs, DOIs via Zenodo). A ROHub RO of a replication is one URL a reviewer can open to see the whole constellation: the workflow and its inputs and outputs, the archived release, the signed FORRT chain, the profile it conforms to and the cited paper, with typed relations between them.

## The path

```bash
pixi run -e rocrate build-rocrate                  # the crate must describe the current release
pixi run -e rocrate deposit-rohub --dry-run        # prints the plan; touches nothing
ROHUB_USERNAME=... ROHUB_PASSWORD=... pixi run -e rocrate deposit-rohub
```

`scripts/deposit_rohub.py` reads `ro-crate-metadata.json` and builds the RO through ROHub's API:

1. **Creates** the RO with title, description, type and research areas set from the start.
2. Adds the crate's local files as **internal resources** in their folders, and its input datasets as external ones.
3. Adds the release, the six nanopublications (type *Nanopublication*), the profiles, the repository and the citations as **typed external resources**.
4. Sets authors, licence, funding and study area, and uploads the **sketch** (the RO's image).
5. Adds the **relations**: workflow `hasInput` / `hasOutput` / `softwareRequirements`; each chain step `wasDerivedFrom` the previous one; the Outcome `wasDerivedFrom` the result files that support it.

It writes `rohub-deposit.json` with the RO id, its PID and every resource id.

## `rohub` settings in `rocrate.json`

```json
"rohub": {
  "research_areas": ["Earth sciences", "Environmental research"],
  "ros_type": "Workflow-centric Research Object",
  "authors": [{"username": "<your ROHub login>"}],
  "sketch": "figures/main_result.png",
  "sketch_title": "Replicated headline result",
  "outcome_evidence": ["results/summary.json"]
}
```

Without `authors`, the crate's authors are matched to ROHub accounts by ORCID (others are added as new agents). Always set a `sketch`: an RO without an image is hard to recognise in listings.

## Lessons from ROHub (why the script works this way)

- **Don't use ROHub's RO-Crate import.** It leaves the description empty, so the RO is flagged as spam and locked: every later edit and even deletion fails. It also drops every entity that is not a `File`. Creating the RO first, with its description, avoids both.
- **Link Zenodo records, not DOIs.** A `doi.org` URL triggers ROHub's enrichment, which mistypes the resource (e.g. as "Taxonomic treatment") and replaces its title. The script uses `zenodo.org/records/<id>` and resolves other DOIs to their landing pages.
- **Never aggregate `ro-crate-metadata.json`** as a resource: the name is reserved and breaks the RO's zip download and preview.
- **Funding** uses ROHub's own convention, grant id `<funder ROR>::<grant number>`; a Crossref funder DOI produces a broken link.
- **Resource titles** are capped at 250 characters.
- **Under load ROHub answers 504 yet creates the RO.** The script then finds the RO by title instead of creating a second one, and retries calls that fail transiently. Deposit one RO at a time.

## Cross-references

- `docs/ro-crate.md`: what the crate contains and where each part comes from.
- `nanopubs/PUBLISHED.md`: the nanopub ledger the crate reads.
