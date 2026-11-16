"""A cell's defect is in its colliders, not only in its looks (QUI-10): checked in MuJoCo.

* A dent: a 1 mm ball dropped on a dent facing up comes to rest lower than on a sound can.
* A corroded terminal: a cell stood on its minus face stands higher or leans, on its crust.
"""

import numpy as np
import pytest

mujoco = pytest.importorskip("mujoco")

from quincaillerie.batteries import write_cell  # noqa: E402
from quincaillerie.sim.checks import DEFAULT, OPTIONS  # noqa: E402
from quincaillerie.sim.mujoco_model import convert, scene  # noqa: E402
from quincaillerie.variation import CellVariation  # noqa: E402

DT = 5e-4
R = 0.00725  # radius of an AA cell (m)
L = 0.0505  # its length
FLOOR = '<geom name="floor" type="plane" size="1 1 0.01"/>'
BALL = '<body name="ball" pos="0 0 {z}"><freejoint/><geom type="sphere" size="0.001" mass="0.0002"/></body>'


def settle(tmp_path, cv, pos, quat, extra="", seconds=0.6):
    asset = tmp_path / f"cell_{cv.defect}.usda"
    write_cell(str(asset), "AA", cv)
    stage = scene(None, [("cell", str(asset), pos, quat, None)])
    xml = convert(stage, options=OPTIONS.format(dt=DT), default=DEFAULT.format(tc=0.002), extra_world=FLOOR + extra)
    model = mujoco.MjModel.from_xml_string(xml)
    data = mujoco.MjData(model)
    for _ in range(int(seconds / DT)):
        mujoco.mj_step(model, data)
    assert np.isfinite(data.qpos).all()
    return model, data


def test_a_ball_rests_lower_in_a_dent(tmp_path):
    depth_mm = 1.0
    # lying along x, dent on top (the dent's angle is measured from +y towards +z)
    heights = {}
    for defect in ("none", "dent"):
        cv = CellVariation(defect=defect, defect_z=0.5, defect_angle_deg=90.0, defect_size=depth_mm, seed=3)
        x0 = (cv.defect_z - 0.5) * (L * 1e3 - 6) * 1e-3  # where the dent is along the can
        model, data = settle(tmp_path, cv, (-x0, 0, R + 0.0002), (1, 0, 0, 0), extra=BALL.format(z=2 * R + 0.004))
        heights[defect] = data.xpos[model.body("ball").id][2] - data.xpos[model.body("cell").id][2]
    drop = (heights["none"] - heights["dent"]) * 1e3
    assert drop > 0.5 * depth_mm, f"the ball rests {drop:.2f} mm lower in the dent, for a {depth_mm} mm dent"


def test_a_cell_stands_on_its_corrosion(tmp_path):
    poses = {}
    for defect in ("none", "corroded_terminal"):
        cv = CellVariation(defect=defect, defect_angle_deg=0.0, defect_size=1.0, seed=3)
        # standing on its minus face: x of the cell turned to +z
        q = (np.cos(-np.pi / 4), 0, np.sin(-np.pi / 4), 0)
        model, data = settle(tmp_path, cv, (0, 0, L / 2 + 0.002), q, seconds=1.0)
        body = model.body("cell").id
        axis = data.xmat[body].reshape(3, 3)[:, 0]  # the cell's x axis in the world
        poses[defect] = (data.xpos[body][2], np.degrees(np.arccos(min(1.0, abs(axis[2])))))
    higher_mm = (poses["corroded_terminal"][0] - poses["none"][0]) * 1e3
    lean_deg = poses["corroded_terminal"][1] - poses["none"][1]
    assert higher_mm > 0.2 or lean_deg > 2.0, f"on its crust: {higher_mm:+.2f} mm, {lean_deg:+.1f} degrees"
