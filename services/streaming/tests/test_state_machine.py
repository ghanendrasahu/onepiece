"""Streaming state machine unit tests."""

import pytest
from worldview_streaming.state_machine import (
    InvalidTransition,
    StreamStatus,
    Transition,
    can_transition,
)


@pytest.mark.parametrize(
    ("current", "target", "expected"),
    [
        ("preparing", "live", True),
        ("preparing", "ended", True),
        ("live", "paused", True),
        ("live", "ended", True),
        ("paused", "live", True),
        ("ended", "archived", True),
        ("live", "archived", False),
        ("archived", "live", False),
        ("preparing", "paused", False),
        ("ended", "live", False),
        ("bogus", "live", False),
    ],
)
def test_transition_table(current, target, expected):
    assert can_transition(current, target) is expected


def test_transition_validate_raises():
    with pytest.raises(InvalidTransition):
        Transition("ended", "live").validate()


def test_all_enum_values_covered_by_table():
    from worldview_streaming import state_machine as sm

    for status in StreamStatus:
        assert status in {s for src in sm._TRANSITIONS for s in [src]}
