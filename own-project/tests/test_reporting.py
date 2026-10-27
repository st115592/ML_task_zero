import csv
import hashlib
import json
import math
from pathlib import Path

import orbit_sim
from report_tools import validate


def test_run_writes_metrics_metadata_and_trajectory(tmp_path):
    orbit_sim.run(tmp_path, [8], repeats=2, source_commit="a" * 40)

    with (tmp_path / "metrics.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    metadata = json.loads((tmp_path / "metadata.json").read_text(encoding="utf-8"))
    with (tmp_path / "trajectory_8.csv").open(encoding="utf-8", newline="") as stream:
        trajectory = list(csv.reader(stream))

    assert {row["method"] for row in rows} == set(orbit_sim.METHODS)
    assert len(rows) == len(orbit_sim.METHODS)
    assert all(int(row["timing_repeats"]) == 2 for row in rows)
    assert all(int(row["memory_measurement_runs"]) == 1 for row in rows)
    assert metadata["source_commit"] == "a" * 40
    assert (
        metadata["source_sha256"]
        == hashlib.sha256(
            Path(orbit_sim.__file__).read_text(encoding="utf-8").encode("utf-8")
        ).hexdigest()
    )
    assert len(trajectory) == 10
    assert trajectory[0] == ["time_s", "x_m", "y_m", "vx_m_s", "vy_m_s"]
    assert all(math.isfinite(float(value)) for row in trajectory[1:] for value in row)


def test_checked_in_report_matches_saved_results():
    repo_root = Path(__file__).resolve().parents[2]
    assert validate(repo_root) == []
