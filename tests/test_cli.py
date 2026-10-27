import os

from quincaillerie import __version__
from quincaillerie.cli import main


def test_version(capsys):
    try:
        main(["--version"])
    except SystemExit:
        pass
    assert __version__ in capsys.readouterr().out


def test_list(capsys):
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    assert "M12" in out and "CR2032" in out and "zinc_clear" in out


def test_generate_and_blender_addon(tmp_path, capsys):
    assert main(["generate", "washer", "M5", "--with", "nut", "--no-scene", "--out", str(tmp_path)]) == 0
    assert sorted(os.listdir(tmp_path / "ISO7089_M5" / "assets")) == ["ISO4032_M5_000.usdc", "ISO7089_M5_000.usda"]
    assert main(["generate", "nut", "M5", "--nominal", "--no-scene", "--out", str(tmp_path / "nominal")]) == 0
    assert os.listdir(tmp_path / "nominal" / "ISO4032_M5" / "assets") == ["ISO4032_M5.usdc"]
    assert main(["generate", "screw", "M5", "--with", "holder", "--out", str(tmp_path)]) == 2
    script = tmp_path / "q.py"
    assert main(["blender-addon", "--out", str(script)]) == 0
    assert "class QUINCAILLERIE_USDHook" in script.read_text()
    import zipfile

    assert main(["blender-addon", "--out", str(tmp_path / "q.zip")]) == 0
    names = zipfile.ZipFile(tmp_path / "q.zip").namelist()
    assert sorted(names) == ["__init__.py", "blender_manifest.toml"]


def test_no_physics(tmp_path):
    from pxr import Usd, UsdPhysics

    assert main(["generate", "holder", "AA", "--with", "cell", "--no-physics", "--out", str(tmp_path)]) == 0
    for f in (tmp_path / "Holder_AA" / "assets").iterdir():
        st = Usd.Stage.Open(str(f))
        assert not any(p.HasAPI(UsdPhysics.RigidBodyAPI) or p.HasAPI(UsdPhysics.CollisionAPI) for p in st.Traverse())
        assert not any(p.IsA(UsdPhysics.Joint) for p in st.Traverse())
