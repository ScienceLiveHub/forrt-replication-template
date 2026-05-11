# `nanopubs/` — FORRT nanopublication chain workspace

This directory holds the field-by-field drafts of the FORRT chain, plus the registry of published URIs. The chain is published manually on `https://platform.sciencelive4all.org` — Claude does not publish; Claude drafts each step in `drafts/`, you review and copy-paste into the platform UI, and the resulting URI goes into `PUBLISHED.md`.

## The chain

A complete FORRT chain is six steps published in order. **Step 1 has three alternative anchor templates** — pick the one that matches your chain shape (see `docs/chain-decision-tree.md`) and **delete the other two** before drafting, so the directory reflects the chain you're actually building:

| Step | Draft file | Template |
|---|---|---|
| 1 (paper-rooted) | `drafts/01_quote.md` | Quote-with-comment |
| 1 (question-rooted, comparative) | `drafts/01_pico.md` | PICO Research Question |
| 1 (question-rooted, descriptive) | `drafts/01_pcc.md` | PCC Research Question |
| 2 | `drafts/02_aida.md` | AIDA Sentence |
| 3 | `drafts/03_claim.md` | FORRT Claim |
| 4 | `drafts/04_study.md` | FORRT Replication Study |
| 5 | `drafts/05_outcome.md` | FORRT Replication Outcome |
| 6 | `drafts/06_citation.md` | CiTO Citation |

Once the chain shape is decided, delete the two step-1 alternatives you aren't using:

```bash
# Paper-rooted chain — keep 01_quote.md:
rm nanopubs/drafts/01_pico.md nanopubs/drafts/01_pcc.md

# Question-rooted, comparative (PICO) — keep 01_pico.md:
rm nanopubs/drafts/01_quote.md nanopubs/drafts/01_pcc.md

# Question-rooted, descriptive (PCC) — keep 01_pcc.md:
rm nanopubs/drafts/01_quote.md nanopubs/drafts/01_pico.md
```

Keeping all three confuses the audit trail: a reader of the finished repo can't tell which anchor the chain was actually built from.

## Drafting workflow

For each step:

1. Run the pre-flight checklist in `docs/forrt-form-fields.md` — before drafting any content.
2. Open the matching draft file in `drafts/`.
3. Write each form field verbatim, in form order. Required fields: provide a value. Optional fields: provide a value, or write `*(skip — optional)*`.
4. Have the user review.
5. The user copy-pastes into the platform UI on `https://platform.sciencelive4all.org` and publishes.
6. The user records the resulting URI in `PUBLISHED.md`.
7. The next step's draft references the just-published URI (e.g. the AIDA's *Relates to this nanopublication* field is the Quote URI).

## Order matters

Each step in the chain references the URI of the previous step:

- AIDA *Relates to* → Quote URI (or PICO/PCC URI)
- FORRT Claim *Search for an AIDA* → AIDA URI
- Replication Study *Search for a FORRT claim* → Claim URI
- Replication Outcome *Search for a FORRT replication study* → Study URI
- CiTO Citation *citing creative work* → Outcome URI

Don't try to publish out of order. Don't forget to update `PUBLISHED.md` as you go — downstream drafts pull from there.

## Optional layers

Once the six-step chain is published, two optional further nanopubs may apply:

- **Research Software** — when the repo *produces* a reusable software artefact (an upstream library, not a one-off demo). Cites back to the FORRT Claim URI as `Research Project`. Drafted in `drafts/07_research_software.md`. See `docs/forrt-form-fields.md` § Research Software and `CLAUDE.md` § Layered architecture: FORRT vs Research Software.
- **Research Synthesis** — when this chain is one of several testing facets of a shared underlying property. Drafted in `drafts/08_synthesis.md`. See `docs/forrt-form-fields.md` § Research Synthesis.

## What lives in `drafts/` after publishing

After a draft has been published, it stays on disk as the historical record of what was submitted. The `PUBLISHED.md` registry is the canonical source for URIs; the drafts are the canonical source for content (including any optional fields skipped).

If a republish is needed (e.g. the platform rejected the original), edit the draft and republish. Don't delete drafts.
