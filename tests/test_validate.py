"""Every generated file passes OpenUSD's own validators (what usdchecker runs)."""

from pathlib import Path

import pytest

from quincaillerie.validate import main, usd_files, validate


@pytest.mark.parametrize("fixture", ["small_set", "varied_set"])
def test_openusd_validators(fixture, request):
    files = usd_files([request.getfixturevalue(fixture).out_dir])
    assert any(f.parent.name == "materials" for f in files)  # the shared material library too
    assert any(f.name == "scene.usda" for f in files)
    for f in files:
        assert validate(f) == [], f.name


def test_command_line(small_set, capsys):
    assert main([str(Path(small_set.out_dir))]) == 0
    assert "0 with issues" in capsys.readouterr().out
