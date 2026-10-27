import numpy as np

from quincaillerie.fasteners import hex_prism
from quincaillerie.threads import iso_profile, mesh_mass_props, nut_mesh, segments, threaded_bolt_mesh


def test_iso_profile_m8():
    p = iso_profile(0.008, 0.00125)
    assert abs(p["d2"] - 0.0071881) < 1e-6  # pitch diameter
    assert abs(p["d3"] - 0.0064664) < 1e-6
    assert abs(p["H"] - np.sqrt(3) / 2 * 0.00125) < 1e-12


def test_mass_properties_of_a_hex_prism():
    s, h = 0.013, 0.005
    V, F = hex_prism(s, 0.0, h)
    vol, m, com, inertia = mesh_mass_props(V, F, 1000.0)
    area = np.sqrt(3) / 2 * s**2
    assert abs(vol - area * h) / (area * h) < 1e-9
    assert np.allclose(com, (0, 0, h / 2), atol=1e-12)
    assert inertia[0, 0] > 0 and abs(inertia[0, 0] - inertia[1, 1]) < 1e-12 * m


def test_threaded_meshes_are_closed_and_positive():
    p = iso_profile(0.006, 0.001)
    for V, F in (threaded_bolt_mesh(p, 0.012, 5e-5, nt=48), nut_mesh(p, 0.010, 0.005, 5e-5, nt=48)):
        vol = mesh_mass_props(V, F, 1.0)[0]
        assert vol > 0
        edges = np.sort(np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), axis=1)
        _, counts = np.unique(edges, axis=0, return_counts=True)
        assert (counts == 2).all()  # watertight: every edge shared by two faces


def test_thread_pieces_stay_inside_the_part_and_clear_each_other():
    p = iso_profile(0.008, 0.00125)
    bolt = segments(p, 0.0, 0.02, 5e-5, "bolt")
    nut = segments(p, 0.0, 0.0068, 5e-5, "nut", s_af=0.013)
    assert all(pts[:, 2].min() >= 0 and pts[:, 2].max() <= 0.02 for pts in bolt)
    rb = max(np.hypot(pts[:, 0], pts[:, 1]).max() for pts in bolt)
    rn = min(np.hypot(pts[:, 0], pts[:, 1]).min() for pts in nut)
    assert rb < 0.004 and rn > p["d1"] / 2  # the bolt crest inside d/2, the nut crest outside d1/2
    assert len(bolt) > 400 and len(nut) > 100
