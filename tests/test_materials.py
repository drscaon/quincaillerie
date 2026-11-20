import os

import pytest
from pxr import Usd

from quincaillerie.materials import FINISHES, MATERIALS


def test_library(small_set):
    lib = os.path.join(small_set.out_dir, "materials", "quincaillerie_materials.usda")
    st = Usd.Stage.Open(lib)
    names = [p.GetName() for p in st.GetPrimAtPath("/Materials").GetChildren()]
    assert set(names) == set(MATERIALS) and set(FINISHES) <= set(names)
    tex = os.listdir(os.path.join(small_set.out_dir, "materials", "textures"))
    assert {"noise_rough.png", "plastic_normal.png", "label_AA.png"} <= set(tex)


def test_materialx_document_is_valid(small_set):
    import pytest

    pytest.importorskip("MaterialX")
    import json

    with open(os.path.join(small_set.out_dir, "manifest.json")) as f:
        assert json.load(f)["summary"]["materials"]["materialx_valid"] is True


def test_labels_have_the_proportions_of_what_they_are_printed_on(tmp_path):
    """A label's pixels are square on the cell: its image has the wrapper's length / circumference
    (the 9V: the label's length / height), so the print is not stretched."""
    import math

    from PIL import Image

    from quincaillerie.catalog import CELLS, label_9v_size, wrapper_span
    from quincaillerie.materials import CELL_FORMATS, make_textures

    make_textures(str(tmp_path))
    for f in CELL_FORMATS:
        x0, x1, r = wrapper_span(CELLS[f])
        w, h = Image.open(tmp_path / f"label_{f}.png").size
        assert w / h == pytest.approx((x1 - x0) / (2 * math.pi * r), rel=0.002), f
    w, h = Image.open(tmp_path / "label_9V.png").size
    lw, lh = label_9v_size(CELLS["9V"])
    assert w / h == pytest.approx(lw / lh, rel=0.002)
