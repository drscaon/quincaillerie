"""Blender: the add-on sets rigid bodies up on import and the parts keep together (needs bpy)."""

import pytest

pytest.importorskip("bpy")

from quincaillerie.blender.checks import blender_test  # noqa: E402


@pytest.mark.parametrize("only", ["drop_ISO4017_M4x10", "nut_on_screw_M4", "holder_AA", "seated_AA"])
def test_blender_gravity(small_set, only):
    rows = blender_test(small_set.out_dir, only=only, verbose=False)
    assert rows and all(r["ok"] for r in rows), rows
