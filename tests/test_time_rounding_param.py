"""Additional parameterized tests for time rounding utilities."""
import pytest
from app.utils.time_rounding import round_time_duration


@pytest.mark.unit
@pytest.mark.parametrize(
    "seconds, interval, method, expected",
    [
        pytest.param(3720, 5, "nearest", 3600, id="62m->nearest-5m=60m"),
        pytest.param(3780, 5, "nearest", 3900, id="63m->nearest-5m=65m"),
        pytest.param(120, 5, "nearest", 0, id="2m->nearest-5m=0"),
        pytest.param(180, 5, "nearest", 300, id="3m->nearest-5m=5m"),
        pytest.param(3720, 15, "up", 4500, id="62m->up-15m=75m"),
        pytest.param(3600, 15, "up", 3600, id="60m->up-15m=60m"),
        pytest.param(3660, 15, "up", 4500, id="61m->up-15m=75m"),
        pytest.param(3720, 15, "down", 3600, id="62m->down-15m=60m"),
        pytest.param(4440, 15, "down", 3600, id="74m->down-15m=60m"),
        pytest.param(4500, 15, "down", 4500, id="75m->down-15m=75m"),
        pytest.param(3720, 60, "nearest", 3600, id="62m->nearest-60m=60m"),
        pytest.param(5400, 60, "nearest", 7200, id="90m->nearest-60m=120m"),
        pytest.param(5340, 60, "nearest", 3600, id="89m->nearest-60m=60m"),
    ],
)
def test_round_time_duration_parametrized(seconds, interval, method, expected):
    assert round_time_duration(seconds, interval, method) == expected


