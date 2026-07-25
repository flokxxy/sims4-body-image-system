"""Pure domain types for body-image reactions."""

from enum import Enum


class Axis(str, Enum):
    FAT = "fat"
    FIT = "fit"


class Direction(str, Enum):
    UP = "up"
    DOWN = "down"


class Goal(str, Enum):
    LOSE_WEIGHT = "lose_weight"
    GAIN_WEIGHT = "gain_weight"
    GAIN_MUSCLE = "gain_muscle"
    MAINTAIN = "maintain"
    NONE = "none"


class EsteemTier(str, Enum):
    LOW = "low"
    NEUTRAL = "neutral"
    HIGH = "high"


class Magnitude(str, Enum):
    NONE = "none"
    NOTICEABLE = "noticeable"
    SHARP = "sharp"


class RelationToGoal(str, Enum):
    PROGRESS = "progress"
    REGRESS = "regress"
    VIOLATION = "violation"
    IRRELEVANT = "irrelevant"
    NO_GOAL = "no_goal"


def esteem_tier(value):
    """Map the persisted self-esteem statistic value to a tier."""
    if value <= 30:
        return EsteemTier.LOW
    if value <= 70:
        return EsteemTier.NEUTRAL
    return EsteemTier.HIGH


def magnitude_from_delta(delta, appearance_focused=False):
    """Bucket an absolute daily Fat/Fit delta according to the spec."""
    noticeable = 2.5 if appearance_focused else 5
    sharp = 7 if appearance_focused else 15
    amount = abs(delta)

    if amount < noticeable:
        return Magnitude.NONE
    if amount < sharp:
        return Magnitude.NOTICEABLE
    return Magnitude.SHARP


def direction_from_delta(delta):
    if delta > 0:
        return Direction.UP
    if delta < 0:
        return Direction.DOWN
    return None


def relation_to_goal(goal, axis, direction):
    """Normalize raw body changes into the compact resolver dimension."""
    if goal == Goal.NONE:
        return RelationToGoal.NO_GOAL
    if goal == Goal.MAINTAIN:
        return RelationToGoal.VIOLATION

    progress_changes = {
        Goal.LOSE_WEIGHT: (Axis.FAT, Direction.DOWN),
        Goal.GAIN_WEIGHT: (Axis.FAT, Direction.UP),
        Goal.GAIN_MUSCLE: (Axis.FIT, Direction.UP),
    }
    target = progress_changes.get(goal)

    if target is None or axis != target[0]:
        return RelationToGoal.IRRELEVANT
    if direction == target[1]:
        return RelationToGoal.PROGRESS
    return RelationToGoal.REGRESS

