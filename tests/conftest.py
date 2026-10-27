import pytest


@pytest.fixture(scope="session")
def small_set(tmp_path_factory):
    """An M4 screw with its nut and washer, and an AA cell with its holder, generated once."""
    from quincaillerie import generate, resolve

    out = tmp_path_factory.mktemp("out")
    parts = resolve("screw", "M4", 10, ["nut", "washer"]) + resolve("cell", "AA", with_=["holder"])
    res = generate(parts, str(out), "small", count=2)
    return res
