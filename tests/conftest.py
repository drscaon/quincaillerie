import pytest


@pytest.fixture(scope="session")
def small_set(tmp_path_factory):
    """An M4 screw with its nut and washer, and an AA cell with its holder, generated once."""
    from quincaillerie import generate, resolve

    out = tmp_path_factory.mktemp("out")
    parts = resolve("screw", "M4", 10, ["nut", "washer"]) + resolve("cell", "AA", with_=["holder"])
    res = generate(parts, str(out), "small", count=2, vary=())
    return res


@pytest.fixture(scope="session")
def varied_set(tmp_path_factory):
    """Five varied instances of an M6 screw and its nut, and of an AA cell and its holder."""
    from quincaillerie import generate, resolve

    out = tmp_path_factory.mktemp("varied")
    parts = resolve("screw", "M6", 12, ["nut"]) + resolve("cell", "AA", with_=["holder"])
    return generate(parts, str(out), "varied", count=5, defect_rate=0.5, seed=3, detail="low")
