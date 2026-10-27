"""Compare basic integrators for a circular Earth orbit; all values use SI units."""

import argparse
import csv
import hashlib
import json
import math
import platform
import statistics
import sys
import time
import tracemalloc
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

MU = 3.986004418e14  # m^3/s^2
R = 7_000_000.0  # m from Earth's center
V = math.sqrt(MU / R)
PERIOD = 2 * math.pi * math.sqrt(R**3 / MU)
METHODS = ("euler", "rk4", "verlet")
Vec = tuple[float, float]


def add(a: Vec, b: Vec) -> Vec:
    return a[0] + b[0], a[1] + b[1]


def mul(k: float, a: Vec) -> Vec:
    return k * a[0], k * a[1]


def acceleration(r: Vec) -> Vec:
    r2 = r[0] ** 2 + r[1] ** 2
    if r2 == 0:
        raise ValueError("spacecraft cannot be at the force singularity")
    return mul(-MU / (r2 * math.sqrt(r2)), r)


def energy(r: Vec, v: Vec) -> float:
    radius = math.hypot(*r)
    if radius == 0:
        raise ValueError("spacecraft cannot be at the force singularity")
    return 0.5 * (v[0] ** 2 + v[1] ** 2) - MU / radius


def angular_momentum(r: Vec, v: Vec) -> float:
    return r[0] * v[1] - r[1] * v[0]


def exact_position(t: float) -> Vec:
    angle = 2 * math.pi * t / PERIOD
    return R * math.cos(angle), R * math.sin(angle)


def _derivative(r: Vec, v: Vec) -> tuple[Vec, Vec]:
    return v, acceleration(r)


def _rk4(r: Vec, v: Vec, dt: float) -> tuple[Vec, Vec]:
    k1 = _derivative(r, v)
    k2 = _derivative(add(r, mul(dt / 2, k1[0])), add(v, mul(dt / 2, k1[1])))
    k3 = _derivative(add(r, mul(dt / 2, k2[0])), add(v, mul(dt / 2, k2[1])))
    k4 = _derivative(add(r, mul(dt, k3[0])), add(v, mul(dt, k3[1])))
    dr = add(add(k1[0], mul(2, k2[0])), add(mul(2, k3[0]), k4[0]))
    dv = add(add(k1[1], mul(2, k2[1])), add(mul(2, k3[1]), k4[1]))
    return add(r, mul(dt / 6, dr)), add(v, mul(dt / 6, dv))


def simulate(method: str, dt: float, steps: int) -> list[tuple[float, Vec, Vec]]:
    if method not in METHODS:
        raise ValueError(f"method must be one of {METHODS}")
    if not math.isfinite(dt) or dt <= 0 or steps <= 0:
        raise ValueError("dt and steps must be positive")
    r: Vec = (R, 0.0)
    v: Vec = (0.0, V)
    result = [(0.0, r, v)]
    for i in range(1, steps + 1):
        if method == "euler":
            a = acceleration(r)
            r, v = add(r, mul(dt, v)), add(v, mul(dt, a))
        elif method == "rk4":
            r, v = _rk4(r, v, dt)
        else:
            a = acceleration(r)
            next_r = add(add(r, mul(dt, v)), mul(dt * dt / 2, a))
            next_a = acceleration(next_r)
            v, r = add(v, mul(dt / 2, add(a, next_a))), next_r
        result.append((i * dt, r, v))
    return result


def metrics(samples: list[tuple[float, Vec, Vec]]) -> dict[str, float]:
    e0 = energy(samples[0][1], samples[0][2])
    h0 = angular_momentum(samples[0][1], samples[0][2])
    pos_err = energy_drift = momentum_drift = 0.0
    for t, r, v in samples:
        exact = exact_position(t)
        pos_err = max(pos_err, math.hypot(r[0] - exact[0], r[1] - exact[1]) / R)
        energy_drift = max(energy_drift, abs(energy(r, v) - e0) / abs(e0))
        momentum_drift = max(momentum_drift, abs(angular_momentum(r, v) - h0) / abs(h0))
    return {
        "max_relative_position_error": pos_err,
        "max_relative_energy_drift": energy_drift,
        "max_relative_angular_momentum_drift": momentum_drift,
    }


def _measure(method: str, dt: float, steps: int, repeats: int):
    times = []
    for _ in range(repeats):
        start = time.perf_counter()
        timed_samples = simulate(method, dt, steps)
        times.append(time.perf_counter() - start)
        del timed_samples

    tracemalloc.start()
    try:
        samples = simulate(method, dt, steps)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return samples, statistics.median(times), peak


def run(output: Path, counts: list[int], repeats: int) -> None:
    if not counts or min(counts) < 4 or repeats < 1:
        raise ValueError("counts must be >= 4 and repeats must be positive")
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for n in counts:
        dt = PERIOD / n
        for method in METHODS:
            samples, seconds, memory = _measure(method, dt, n, repeats)
            rows.append(
                {
                    "method": method,
                    "steps_per_orbit": n,
                    "dt_s": dt,
                    **metrics(samples),
                    "median_runtime_s": seconds,
                    "peak_traced_memory_bytes": memory,
                    "timing_repeats": repeats,
                    "memory_measurement_runs": 1,
                }
            )
            if method == "rk4":
                with (output / f"trajectory_{n}.csv").open(
                    "w", newline="", encoding="utf-8"
                ) as stream:
                    writer = csv.writer(stream)
                    writer.writerow(("time_s", "x_m", "y_m", "vx_m_s", "vy_m_s"))
                    writer.writerows((t, r[0], r[1], v[0], v[1]) for t, r, v in samples)
    with (output / "metrics.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    tool_versions = {}
    for name in ("pytest", "ruff", "ty"):
        try:
            tool_versions[name] = version(name)
        except PackageNotFoundError:
            tool_versions[name] = None
    metadata = {
        "model": "planar massless spacecraft, fixed Newtonian point-mass Earth",
        "units": {
            "position": "m",
            "time": "s",
            "velocity": "m/s",
            "mu": "m^3/s^2",
            "specific_energy": "m^2/s^2",
        },
        "mu_m3_s2": MU,
        "initial_radius_m": R,
        "initial_speed_m_s": V,
        "analytic_period_s": PERIOD,
        "methods": list(METHODS),
        "steps_per_orbit": counts,
        "timing_repeats": repeats,
        "memory_measurement_runs": 1,
        "random_seed": None,
        "randomness": "none; deterministic",
        "python": sys.version,
        "platform": platform.platform(),
        "tool_versions": tool_versions,
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "timing_note": "timed without tracemalloc; compare only on the same hardware",
    }
    (output / "metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results"))
    parser.add_argument("--steps-per-orbit", default="100,200,400")
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    run(args.output, [int(n) for n in args.steps_per_orbit.split(",")], args.repeats)


if __name__ == "__main__":
    main()
