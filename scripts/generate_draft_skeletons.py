#!/usr/bin/env python3
"""Generate the field skeleton of each nanopub draft from the template snapshot.

The drafts in `nanopubs/drafts/` are what the `nanopub-drafter` agent fills in
and the user copy-pastes into the Science Live UI. Each draft is two things at
once: hand-written *guidance* (why the version DOI not the concept DOI, the AIDA
atomic rule, platform-bug workarounds — none of it derivable from a template)
and a *field enumeration* that must match the template exactly. The field
enumeration is the part that drifts: outcomes have shipped missing two of the
five validation-status values, an AIDA draft missing the research-project field.

So each draft carries its field enumeration inside a generated region:

    <!-- FIELDS:GENERATED step=05_outcome ... -->
    ### 1. Short URI suffix for the outcome  ·  URI · required
    ...
    <!-- /FIELDS:GENERATED -->

This script rewrites *only* what is between those markers, from
`nanopubs/templates/fields.snapshot.json` (which is itself pinned to the live
templates by `check_template_drift.py`). Everything outside the markers — all
the guidance — is left untouched. So the field lists can never silently drift
from the templates again, and the guidance is never clobbered.

    pixi run -e tests gen-drafts           # rewrite the generated regions in place
    pixi run -e tests gen-drafts --check   # exit 1 if any region is out of date

`--check` runs in CI (offline: it reads the committed snapshot, no network), so
a draft whose generated region was hand-edited, or left stale after a snapshot
update, fails the build.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SNAPSHOT = ROOT / "nanopubs" / "templates" / "fields.snapshot.json"
REGISTRY = ROOT / "nanopubs" / "templates" / "registry.json"
DRAFTS = ROOT / "nanopubs" / "drafts"

OPEN_RE = re.compile(r"<!--\s*FIELDS:GENERATED\s+step=(?P<step>[\w.]+).*?-->", re.DOTALL)
CLOSE = "<!-- /FIELDS:GENERATED -->"

# How many choices to spell out before collapsing to a summary line. The CiTO
# relation vocabulary has 40+; enumerating it as checkboxes would bury the draft.
MAX_ENUMERATED_CHOICES = 15

_KIND_LABEL = {
    "literal": "text",
    "long_literal": "text (long)",
    "uri": "URI",
    "auto_escape_uri": "URI",
    "external_uri": "URL or DOI",
    "guided_choice": "search / select",
    "restricted_choice": "choice",
}


def _cap_from_regex(regex: str | None) -> str | None:
    """Turn an nt:hasRegex length bound like `[\\s\\S]{5,800}` into `max 800 chars`."""
    if not regex:
        return None
    m = re.search(r"\{(\d+),(\d+)\}", regex)
    return f"max {m.group(2)} chars" if m else None


def render_field(n: int, f: dict) -> list[str]:
    kind = _KIND_LABEL.get(f["kind"], f["kind"])
    req = "required" if f["required"] else "optional"
    bits = [kind, req]
    if f.get("repeatable"):
        bits.append("repeatable")
    cap = _cap_from_regex(f.get("regex"))
    if cap:
        bits.append(cap)
    if f.get("prefix"):
        bits.append(f"prefix `{f['prefix']}`")

    lines = [f"### {n}. {f['label']}", "", f"*{' · '.join(bits)}*", ""]

    choices = f.get("possible_values", [])
    if f["kind"] == "restricted_choice":
        if len(choices) <= MAX_ENUMERATED_CHOICES:
            for c in choices:
                lines.append(f"- [ ] {c['label']}")
            lines.append("")
        else:
            src = f.get("values_from", [])
            src_note = f" (see {src[0]})" if src else ""
            lines.append(f"Choose one of {len(choices)} values from the controlled "
                         f"vocabulary{src_note}. See the field notes below for the "
                         f"FORRT-relevant subset.")
            lines.append("")
    elif f["kind"] == "guided_choice":
        lines.append("_Search / select in the UI; type to filter._")
        lines.append("")
        lines.append("```")
        lines.append("")
        lines.append("```")
        lines.append("")
    else:
        lines.append("```")
        lines.append("")
        lines.append("```")
        lines.append("")
    return lines


def render_region(step: str, spec: dict, registry: dict) -> str:
    meta = registry["steps"].get(step, {})
    header = [
        f"**Template:** {spec.get('label','')}  ",
        f"**Template URI:** {meta.get('current','(not in registry)')}  ",
        f"*{len(spec['fields'])} fields, in form order. This block is generated from "
        f"`nanopubs/templates/fields.snapshot.json`; edit guidance outside the markers, "
        f"not here.*",
        "",
    ]
    body: list[str] = []
    for i, f in enumerate(spec["fields"], 1):
        body.extend(render_field(i, f))
    return "\n".join(header + body).rstrip() + "\n"


def process(path: Path, snapshot: dict, registry: dict) -> tuple[str, str] | None:
    """Return (step, new_text) if the file has a generated region, else None."""
    text = path.read_text()
    m = OPEN_RE.search(text)
    if not m:
        return None
    step = m.group("step")
    close_at = text.find(CLOSE, m.end())
    if close_at == -1:
        raise ValueError(f"{path.name}: opening FIELDS:GENERATED marker has no closing "
                         f"{CLOSE}")
    if step not in snapshot:
        raise ValueError(f"{path.name}: step {step!r} not in the snapshot")

    region = render_region(step, snapshot[step], registry)
    new_text = text[:m.end()] + "\n" + region + text[close_at:]
    return step, new_text


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--check", action="store_true",
                   help="Do not write; exit 1 if any generated region is out of date.")
    args = p.parse_args(argv)

    snapshot = json.loads(SNAPSHOT.read_text())["steps"]
    registry = json.loads(REGISTRY.read_text())

    stale: list[str] = []
    written: list[str] = []
    for path in sorted(DRAFTS.glob("*.md")):
        result = process(path, snapshot, registry)
        if result is None:
            continue
        step, new_text = result
        if new_text == path.read_text():
            continue
        if args.check:
            stale.append(path.name)
        else:
            path.write_text(new_text)
            written.append(path.name)

    if args.check:
        if stale:
            print("Draft field skeletons are out of date with the template snapshot:",
                  file=sys.stderr)
            for name in stale:
                print(f"  - {name}", file=sys.stderr)
            print("\nRegenerate with `pixi run -e tests gen-drafts` and commit.",
                  file=sys.stderr)
            return 1
        print("OK — all draft field skeletons match the snapshot.", file=sys.stderr)
        return 0

    if written:
        print(f"Rewrote generated regions in: {', '.join(written)}", file=sys.stderr)
    else:
        print("No changes — all generated regions already current.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
