import math
import tracemalloc

import pytest

import orbit_sim
from orbit_sim import (
    MU,
    PERIOD,
    R,
    acceleration,
    angular_momentum,
    energy,
    metrics,
    simulate,
)


def test_circular_force_balance():
    speed = math.sqrt(MU / R)
    assert acceleration((R, 0))[0] == pytest.approx(-(speed**2) / R)
    assert acceleration((R, 0))[1] == pytest.approx(0, abs=1e-14)


@pytest.mark.parametrize(
    ("method", "energy_limit", "momentum_limit"),
    [("euler", 0.16, 0.09), ("rk4", 1e-8, 1e-8), ("verlet", 2e-8, 1e-12)],
)
def test_invariants_remain_within_method_specific_limits(
    method, energy_limit, momentum_limit
):
    result = metrics(simulate(method, PERIOD / 400, 400))
    assert result["max_relative_energy_drift"] < energy_limit
    assert result["max_relative_angular_momentum_drift"] < momentum_limit
    assert math.isfinite(result["max_relative_position_error"])


@pytest.mark.parametrize(
    ("method", "min_ratio", "max_ratio"),
    [("euler", 1.2, 2.8), ("rk4", 8.0, 32.0), ("verlet", 3.2, 4.8)],
)
def test_position_error_converges_at_expected_order(method, min_ratio, max_ratio):
    coarse = metrics(simulate(method, PERIOD / 100, 100))
    fine = metrics(simulate(method, PERIOD / 200, 200))
    ratio = coarse["max_relative_position_error"] / fine["max_relative_position_error"]
    assert min_ratio < ratio < max_ratio


def test_measure_times_without_tracing_and_measures_single_run_memory(monkeypatch):
    tracing_states = []

    def fake_simulate(method, dt, steps):
        tracing_states.append(tracemalloc.is_tracing())
        return [(0.0, (R, 0.0), (0.0, math.sqrt(MU / R)))]

    monkeypatch.setattr(orbit_sim, "simulate", fake_simulate)
    _, elapsed, peak = orbit_sim._measure("rk4", PERIOD / 10, 10, repeats=2)

    assert tracing_states == [False, False, True]
    assert elapsed >= 0
    assert peak > 0


@pytest.mark.parametrize("dt,steps", [(0.0, 5), (-1.0, 5), (1.0, 0)])
def test_bad_inputs_are_rejected(dt, steps):
    with pytest.raises(ValueError):
        simulate("rk4", dt, steps)


def test_singularity_and_reference_invariants():
    with pytest.raises(ValueError):
        acceleration((0, 0))
    r, v = (R, 0), (0, math.sqrt(MU / R))
    assert energy(r, v) == pytest.approx(-MU / (2 * R))
    assert angular_momentum(r, v) == pytest.approx(R * v[1])

