"""Which defects stop a nut? The experiment behind docs/jam-rate.md.

Generates M6 x 16 screws with every defect kind (defect rate 1) and without any (defect rate 0),
then drives one sound, nominal nut along each screw in MuJoCo with a light torque:

* crushed thread: the nut starts next to the damaged zone and is driven into it (the same check
  as `quincaillerie sim-test --defects`); "stopped" when it travels less than on a sound screw;
* anything else: the nut is driven from the head to the tip; the distance travelled is recorded.

Slow: about 50 s per screw on one CPU core (40 screws, 2 cores: 17 minutes).

    pip install "quincaillerie[sim]"
    python scripts/jam_experiment.py            # writes docs/jam_experiment.json
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from multiprocessing import Pool
from pathlib import Path

from quincaillerie import generate, resolve
from quincaillerie.sim.checks import inventory, jam, through

SIZE, LENGTH = "M6", 16
DEFECTIVE, SOUND = 30, 10  # screws drawn with a defect, and without


def _sets(root):
    """The three sets: nominal screw and nut, screws with defects, screws without."""
    kw = dict(detail="low", scene=False)
    screw = resolve("screw", SIZE, LENGTH)
    nominal = generate(resolve("screw", SIZE, LENGTH, ["nut"]), root / "nominal", vary=(), **kw)
    bad = generate(screw, root / "bad", count=DEFECTIVE, defect_rate=1.0, seed=11, **kw)
    good = generate(screw, root / "good", count=SOUND, defect_rate=0.0, seed=12, **kw)
    return nominal.out_dir, bad.out_dir, good.out_dir


def _one(job):
    """One screw (run in a worker process: the inventories are read again there)."""
    nominal_dir, set_dir, name = job
    nominal = inventory(nominal_dir)
    nut = next(a for a in nominal.values() if a["kind"] == "nut")
    sound = next(a for a in nominal.values() if a["kind"] == "screw")
    screw = inventory(set_dir)[name]
    t0 = time.time()
    row = dict(
        screw=name,
        defect=screw["defect"],
        defect_size=screw["attrs"].get("variation:defect_size"),
        clearance_mm=screw["attrs"].get("variation:clearance_mm"),
    )
    if screw["defect"] == "crushed_thread":
        r = jam(screw, nut, SIZE, sound)
        row.update(
            test="into the zone", travel_mm=r["travel_mm"], sound_travel_mm=r["sound_travel_mm"], stopped=r["stopped"]
        )
    else:
        row.update(test="head to tip", travel_mm=through(screw, nut, SIZE))
    row["wall_s"] = round(time.time() - t0, 1)
    print(json.dumps(row), flush=True)
    return row


def main(out="docs/jam_experiment.json"):
    with tempfile.TemporaryDirectory() as tmp:
        nominal_dir, bad_dir, good_dir = _sets(Path(tmp))
        jobs = [
            (nominal_dir, d, name)
            for d in (bad_dir, good_dir)
            for name, a in inventory(d).items()
            if a["kind"] == "screw"
        ]
        with Pool(2) as pool:
            rows = pool.map(_one, jobs, chunksize=1)
    Path(out).write_text(json.dumps(dict(size=SIZE, length_mm=LENGTH, screws=rows), indent=1) + "\n")
    print(f"written to {out}")


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
