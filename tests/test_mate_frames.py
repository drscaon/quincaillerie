"""Contract, section 8: where each MateFrame is, measured on the parts' own geometry.

A MateFrame's origin is on the mating plane, +Z is the way the part that goes in moves, and two
parts mate when their MateFrames coincide: a nut on its screw against the head, a socket over the
whole head, a cell seated in its holder exactly as the seated check simulates it.
"""

from pathlib import Path

import numpy as np
import pytest
from pxr import Gf, Usd, UsdGeom

from quincaillerie import contract
from quincaillerie.batteries import FLOOR_T, write_cell, write_holder
from quincaillerie.catalog import CELLS, DEFAULT_LENGTH, METRIC
from quincaillerie.fasteners import write_nut, write_screw
from quincaillerie.scenes import seated_overrides

MM = 1e-3
TOL = 0.05 * MM  # a cell's label is 0.02 mm proud of its can, which the colliders follow


def _points(stage):
    """Every mesh vertex of a part, in its file's coordinates."""
    cache, found = UsdGeom.XformCache(), []
    for prim in stage.Traverse():
        if prim.IsA(UsdGeom.Mesh):
            P = np.asarray(UsdGeom.Mesh(prim).GetPointsAttr().Get(), float)
            M = np.asarray(cache.GetLocalToWorldTransform(prim))
            found.append(P @ M[:3, :3] + M[3, :3])
    return np.vstack(found)


def _frame(stage, name):
    prim = next(p for p in stage.Traverse() if p.GetName() == name)
    return prim, UsdGeom.XformCache().GetLocalToWorldTransform(prim)


def _in_frame(stage, name):
    """The part's vertices in the coordinates of its MateFrame ``name``."""
    _, M = _frame(stage, name)
    M = np.asarray(M)
    return (_points(stage) - M[3, :3]) @ M[:3, :3].T  # the rows of M are the frame's axes


@pytest.fixture(scope="module")
def parts(tmp_path_factory):
    out = tmp_path_factory.mktemp("mate")
    found = {}
    for size in METRIC:
        for kind, write in (("screw", write_screw), ("nut", write_nut)):
            path = str(out / f"{kind}_{size}.usda")
            write(path, size, detail="low")
            found[kind, size] = Usd.Stage.Open(path)
    for fmt in CELLS:
        for kind, write in (("cell", write_cell), ("holder", write_holder)):
            path = str(out / f"{kind}_{fmt}.usda")
            write(path, fmt)
            found[kind, fmt] = Usd.Stage.Open(path)
    return found


@pytest.mark.slow
@pytest.mark.parametrize("size", list(METRIC))
def test_a_nut_whose_frame_coincides_is_on_the_screw_against_its_head(parts, size):
    """Thread: the plane is the face under the head, and the screw goes through the nut along +Z."""
    t, length = METRIC[size], DEFAULT_LENGTH[size] * MM
    screw = _in_frame(parts["screw", size], "MateFrame_thread")[:, 2]
    assert screw.max() == pytest.approx(length, abs=TOL)  # the shank goes in, its whole length
    assert screw.min() == pytest.approx(-t["k"] * MM, abs=TOL)  # the head stays behind the plane
    nut = _in_frame(parts["nut", size], "MateFrame_thread")[:, 2]
    assert nut.min() == pytest.approx(0, abs=TOL)  # the nut's face on the plane...
    assert nut.max() == pytest.approx(t["m"] * MM, abs=TOL)  # ...and the nut along +Z, on the shank


@pytest.mark.parametrize("kind", ["screw", "nut"])
@pytest.mark.parametrize("size", list(METRIC))
def test_a_socket_on_the_drive_frame_holds_the_whole_hex(parts, kind, size):
    """Drive: the plane is where a socket's mouth is; the hex goes in along +Z, as deep as it is."""
    stage = parts[kind, size]
    frame, _ = _frame(stage, "MateFrame_drive")
    engagement = frame.GetAttribute("quincaillerie:engagement").Get()
    z = _in_frame(stage, "MateFrame_drive")[:, 2]
    assert z.max() == pytest.approx(engagement, abs=TOL)
    assert engagement == pytest.approx(METRIC[size]["k" if kind == "screw" else "m"] * MM)


@pytest.mark.parametrize("fmt", list(CELLS))
@pytest.mark.parametrize("terminal", ["MateFrame_plus", "MateFrame_minus"])
def test_a_terminal_frame_is_on_its_tip_and_points_out_of_the_cell(parts, fmt, terminal):
    stage = parts["cell", fmt]
    z = _in_frame(stage, terminal)[:, 2]
    assert z.max() == pytest.approx(0, abs=TOL)  # the contact presses on the tip...
    _, M = _frame(stage, terminal)
    P = _points(stage)
    out = np.asarray(M)[3, :3] - (P.min(axis=0) + P.max(axis=0)) / 2  # from the cell's middle to the terminal
    axis = np.zeros(3)
    axis[np.argmax(abs(out))] = np.sign(out[np.argmax(abs(out))])
    assert np.allclose(np.asarray(M)[2, :3], axis, atol=1e-9)  # ...pushed back along -Z


@pytest.mark.parametrize("fmt", list(CELLS))
def test_a_cell_whose_seat_frame_coincides_with_the_holders_is_seated(parts, fmt):
    """Seat: the plane is the holder's bed, the cell rests on it; the pose the seated check simulates."""
    cell, holder = parts["cell", fmt], parts["holder", fmt]
    assert _in_frame(cell, "MateFrame_seat")[:, 2].max() == pytest.approx(0, abs=TOL)
    _, on_cell = _frame(cell, "MateFrame_seat")
    _, on_holder = _frame(holder, "MateFrame_seat")
    pose = on_cell.GetInverse() * on_holder  # where the cell goes for its frame to be the holder's
    position, quat, _ = seated_overrides(fmt)
    assert np.allclose(pose.ExtractTranslation(), position, atol=1e-9)
    rotation = pose.ExtractRotationQuat()
    assert Gf.Quatd(*quat).GetImaginary() == pytest.approx(rotation.GetImaginary(), abs=1e-9)
    assert pose.ExtractTranslation()[2] == pytest.approx(FLOOR_T * MM)  # its underside on the bed


def test_a_varied_cell_rests_on_the_bed_by_its_own_size(varied_set):
    """The seat frame of a cell made larger or smaller is where that cell touches the bed."""
    cells = sorted((Path(varied_set.out_dir) / "assets").glob("Cell_*.usd*"))
    cells = [f for f in cells if not contract.is_engine_layer(f)]
    assert cells
    for f in cells:
        stage = Usd.Stage.Open(str(f))
        assert _in_frame(stage, "MateFrame_seat")[:, 2].max() == pytest.approx(0, abs=TOL), f.name
