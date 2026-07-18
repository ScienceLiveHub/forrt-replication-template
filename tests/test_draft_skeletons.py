"""Tests for scripts/generate_draft_skeletons.py.

The generator owns the field enumeration inside each draft's
`<!-- FIELDS:GENERATED -->` markers, rendered from the committed snapshot.
These tests are the offline gate: they run in the ordinary test job (no
network — they read the committed snapshot and drafts) and fail if any draft's
generated region was hand-edited or left stale after a snapshot update. That is
what stops a field list from drifting from the templates again.

Run: pixi run -e tests test
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_draft_skeletons as gen  # noqa: E402

SNAPSHOT = json.loads((ROOT / "nanopubs" / "templates" / "fields.snapshot.json").read_text())["steps"]
REGISTRY = json.loads((ROOT / "nanopubs" / "templates" / "registry.json").read_text())
DRAFTS = sorted((ROOT / "nanopubs" / "drafts").glob("*.md"))
MARKED = [p for p in DRAFTS if gen.OPEN_RE.search(p.read_text())]


def test_every_chain_step_draft_has_a_generated_region():
    """Each step in the registry has exactly one draft carrying its generated
    region (01 has three alternates, so allow the registry's step set as a subset)."""
    steps_with_region = {gen.OPEN_RE.search(p.read_text()).group("step") for p in MARKED}
    assert set(REGISTRY["steps"]) <= steps_with_region


@pytest.mark.parametrize("path", MARKED, ids=[p.name for p in MARKED])
def test_generated_region_is_up_to_date(path):
    """Regenerating in memory must be a no-op — otherwise the committed region
    was hand-edited or the snapshot moved without `gen-drafts` being re-run."""
    step, new_text = gen.process(path, SNAPSHOT, REGISTRY)
    assert new_text == path.read_text(), (
        f"{path.name} field skeleton is stale — run `pixi run -e tests gen-drafts`"
    )


@pytest.mark.parametrize("step", list(SNAPSHOT))
def test_render_region_is_deterministic(step):
    """Rendering a region twice is byte-identical (no unsorted iteration)."""
    a = gen.render_region(step, SNAPSHOT[step], REGISTRY)
    b = gen.render_region(step, SNAPSHOT[step], REGISTRY)
    assert a == b


def test_generated_region_reflects_the_snapshot_vocab():
    """A concrete anti-drift assertion: the outcome draft carries all five
    validation-status values (it once shipped with three)."""
    outcome = next(p for p in MARKED
                   if gen.OPEN_RE.search(p.read_text()).group("step") == "05_outcome")
    _, text = gen.process(outcome, SNAPSHOT, REGISTRY)
    for value in ("validated", "partially supported", "contradicted",
                  "inconclusive", "not tested"):
        assert f"- [ ] {value}" in text


def test_missing_closing_marker_raises(tmp_path):
    bad = tmp_path / "99_bad.md"
    bad.write_text("<!-- FIELDS:GENERATED step=03_claim -->\nno close\n")
    with pytest.raises(ValueError):
        gen.process(bad, SNAPSHOT, REGISTRY)
