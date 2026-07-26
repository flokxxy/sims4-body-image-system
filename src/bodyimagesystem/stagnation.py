"""Pure state machine for goal stagnation.

The game integration will persist ``days_without_progress`` in a hidden
Statistic. This module only decides how that counter changes, so its behavior
can be tested without importing Sims 4 modules or requiring tuning resources.
"""

from collections import namedtuple
from enum import Enum

from bodyimagesystem.domain import Goal, Magnitude, magnitude_from_delta


STAGNATION_DAYS_REQUIRED = 3
DIRECTED_GOALS = frozenset(
    (Goal.LOSE_WEIGHT, Goal.GAIN_WEIGHT, Goal.GAIN_MUSCLE)
)


class StagnationStatus(str, Enum):
    NOT_APPLICABLE = "not_applicable"
    PAUSED = "paused"
    PROGRESS = "progress"
    COUNTING = "counting"
    TRIGGERED = "triggered"


StagnationUpdate = namedtuple(
    "StagnationUpdate",
    ("days_without_progress", "triggered", "status"),
)


def progress_delta_for_goal(goal, fat_delta, fit_delta):
    """Return signed progress, where a positive value moves toward the goal."""
    if goal == Goal.LOSE_WEIGHT:
        return -fat_delta
    if goal == Goal.GAIN_WEIGHT:
        return fat_delta
    if goal == Goal.GAIN_MUSCLE:
        return fit_delta
    return None


def has_meaningful_progress(
    goal,
    fat_delta,
    fit_delta,
    appearance_focused=False,
):
    """Whether the target axis moved far enough in the desired direction."""
    progress_delta = progress_delta_for_goal(goal, fat_delta, fit_delta)
    if progress_delta is None or progress_delta <= 0:
        return False
    return (
        magnitude_from_delta(progress_delta, appearance_focused)
        != Magnitude.NONE
    )


def advance_stagnation(
    current_days,
    goal,
    fat_delta,
    fit_delta,
    appearance_focused=False,
    paused=False,
):
    """Advance the daily stagnation counter by one sampling window.

    Non-directed goals clear the counter. A pause preserves it. Meaningful
    progress clears it. Every other directed-goal day increments it; the third
    consecutive day emits a trigger and resets the counter for a future cycle.
    """
    days = max(0, int(current_days))

    if goal not in DIRECTED_GOALS:
        return StagnationUpdate(0, False, StagnationStatus.NOT_APPLICABLE)

    if paused:
        return StagnationUpdate(days, False, StagnationStatus.PAUSED)

    if has_meaningful_progress(
        goal,
        fat_delta,
        fit_delta,
        appearance_focused,
    ):
        return StagnationUpdate(0, False, StagnationStatus.PROGRESS)

    next_days = days + 1
    if next_days >= STAGNATION_DAYS_REQUIRED:
        return StagnationUpdate(0, True, StagnationStatus.TRIGGERED)

    return StagnationUpdate(next_days, False, StagnationStatus.COUNTING)
