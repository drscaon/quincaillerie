import os

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

    with open(os.path.join(small_set.out_dir, "summary.json")) as f:
        assert json.load(f)["materials"]["materialx_valid"] is True
