import math

import pytest

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
    assert acceleration((R, 0))[0] == pytest.approx(-speed**2 / R)
    assert acceleration((R, 0))[1] == pytest.approx(0, abs=1e-14)


@pytest.mark.parametrize("method", ["euler", "rk4", "verlet"])
def test_invariants_remain_bounded(method):
    result = metrics(simulate(method, PERIOD / 400, 400))
    assert result["max_relative_energy_drift"] < 0.2
    assert result["max_relative_angular_momentum_drift"] < 0.2
    assert math.isfinite(result["max_relative_position_error"])


def test_rk4_error_reduces_when_step_is_halved():
    coarse = metrics(simulate("rk4", PERIOD / 100, 100))
    fine = metrics(simulate("rk4", PERIOD / 200, 200))
    a = fine["max_relative_position_error"]
    b = coarse["max_relative_position_error"]
    assert a < b / 8


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
