"""Pure reaction resolver for daily body changes.

The resolver returns symbolic buff keys instead of tuning instance IDs. This
keeps the complete rule table testable before the corresponding package
resources exist and lets the integration layer map keys to IDs later.
"""

from collections import namedtuple

from bodyimagesystem.domain import (
    EsteemTier,
    Goal,
    Magnitude,
    RelationToGoal,
)


ReactionProfile = namedtuple("ReactionProfile", ("esteem_delta", "label"))
Reaction = namedtuple("Reaction", ("buff_key", "esteem_delta", "label"))

FALLBACK = Reaction(None, 0, "neutral")

DIRECTED_GOALS = frozenset(
    (Goal.LOSE_WEIGHT, Goal.GAIN_WEIGHT, Goal.GAIN_MUSCLE)
)


RULES = {
    # PROGRESS
    (RelationToGoal.PROGRESS, Magnitude.NOTICEABLE, EsteemTier.LOW):
        ReactionProfile(1, "slightly_encouraged"),
    (RelationToGoal.PROGRESS, Magnitude.SHARP, EsteemTier.LOW):
        ReactionProfile(2, "inspired"),
    (RelationToGoal.PROGRESS, Magnitude.NOTICEABLE, EsteemTier.NEUTRAL):
        ReactionProfile(1, "pleased"),
    (RelationToGoal.PROGRESS, Magnitude.SHARP, EsteemTier.NEUTRAL):
        ReactionProfile(2, "confident"),
    (RelationToGoal.PROGRESS, Magnitude.NOTICEABLE, EsteemTier.HIGH):
        ReactionProfile(1, "confident"),
    (RelationToGoal.PROGRESS, Magnitude.SHARP, EsteemTier.HIGH):
        ReactionProfile(2, "proud"),

    # REGRESS
    (RelationToGoal.REGRESS, Magnitude.NOTICEABLE, EsteemTier.LOW):
        ReactionProfile(-1, "worried"),
    (RelationToGoal.REGRESS, Magnitude.SHARP, EsteemTier.LOW):
        ReactionProfile(-3, "depressed"),
    (RelationToGoal.REGRESS, Magnitude.NOTICEABLE, EsteemTier.NEUTRAL):
        ReactionProfile(-1, "upset"),
    (RelationToGoal.REGRESS, Magnitude.SHARP, EsteemTier.NEUTRAL):
        ReactionProfile(-2, "worried"),
    (RelationToGoal.REGRESS, Magnitude.NOTICEABLE, EsteemTier.HIGH):
        ReactionProfile(-1, "slightly_hurt"),
    (RelationToGoal.REGRESS, Magnitude.SHARP, EsteemTier.HIGH):
        ReactionProfile(-1, "upset"),

    # VIOLATION
    (RelationToGoal.VIOLATION, Magnitude.NOTICEABLE, EsteemTier.LOW):
        ReactionProfile(-1, "tense"),
    (RelationToGoal.VIOLATION, Magnitude.SHARP, EsteemTier.LOW):
        ReactionProfile(-2, "worried"),
    (RelationToGoal.VIOLATION, Magnitude.NOTICEABLE, EsteemTier.NEUTRAL):
        ReactionProfile(-1, "slightly_tense"),
    (RelationToGoal.VIOLATION, Magnitude.SHARP, EsteemTier.NEUTRAL):
        ReactionProfile(-1, "tense"),
    (RelationToGoal.VIOLATION, Magnitude.NOTICEABLE, EsteemTier.HIGH):
        ReactionProfile(0, "neutral"),
    (RelationToGoal.VIOLATION, Magnitude.SHARP, EsteemTier.HIGH):
        ReactionProfile(-1, "slightly_worried"),

    # NO_GOAL
    (RelationToGoal.NO_GOAL, Magnitude.NOTICEABLE, EsteemTier.LOW):
        ReactionProfile(-1, "uneasy"),
    (RelationToGoal.NO_GOAL, Magnitude.SHARP, EsteemTier.LOW):
        ReactionProfile(-1, "pensive_uneasy"),
    (RelationToGoal.NO_GOAL, Magnitude.NOTICEABLE, EsteemTier.NEUTRAL):
        ReactionProfile(0, "neutral"),
    (RelationToGoal.NO_GOAL, Magnitude.SHARP, EsteemTier.NEUTRAL):
        ReactionProfile(0, "pensive"),
    (RelationToGoal.NO_GOAL, Magnitude.NOTICEABLE, EsteemTier.HIGH):
        ReactionProfile(0, "neutral"),
    (RelationToGoal.NO_GOAL, Magnitude.SHARP, EsteemTier.HIGH):
        ReactionProfile(1, "calm_acceptance"),

    # IRRELEVANT intentionally ignores self-esteem, but all tier combinations
    # remain explicit so the logical matrix stays complete and auditable.
    (RelationToGoal.IRRELEVANT, Magnitude.NOTICEABLE, EsteemTier.LOW):
        ReactionProfile(0, "neutral"),
    (RelationToGoal.IRRELEVANT, Magnitude.SHARP, EsteemTier.LOW):
        ReactionProfile(1, "pleasantly_surprised"),
    (RelationToGoal.IRRELEVANT, Magnitude.NOTICEABLE, EsteemTier.NEUTRAL):
        ReactionProfile(0, "neutral"),
    (RelationToGoal.IRRELEVANT, Magnitude.SHARP, EsteemTier.NEUTRAL):
        ReactionProfile(1, "pleasantly_surprised"),
    (RelationToGoal.IRRELEVANT, Magnitude.NOTICEABLE, EsteemTier.HIGH):
        ReactionProfile(0, "neutral"),
    (RelationToGoal.IRRELEVANT, Magnitude.SHARP, EsteemTier.HIGH):
        ReactionProfile(1, "pleasantly_surprised"),
}


def _goal_matches_relation(goal, relation):
    if relation in (RelationToGoal.PROGRESS, RelationToGoal.REGRESS):
        return goal in DIRECTED_GOALS
    if relation == RelationToGoal.VIOLATION:
        return goal == Goal.MAINTAIN
    if relation == RelationToGoal.NO_GOAL:
        return goal == Goal.NONE
    if relation == RelationToGoal.IRRELEVANT:
        return goal in DIRECTED_GOALS
    return False


def reaction_buff_key(goal, relation, magnitude, esteem_tier):
    """Build the stable symbolic key used to map a reaction to tuning."""
    if relation in (RelationToGoal.PROGRESS, RelationToGoal.REGRESS):
        return ".".join(
            (relation.value, goal.value, esteem_tier.value, magnitude.value)
        )
    if relation == RelationToGoal.VIOLATION:
        return ".".join(
            (relation.value, Goal.MAINTAIN.value, esteem_tier.value, magnitude.value)
        )
    if relation == RelationToGoal.NO_GOAL:
        return ".".join(
            (relation.value, Goal.NONE.value, esteem_tier.value, magnitude.value)
        )
    if relation == RelationToGoal.IRRELEVANT:
        return ".".join((relation.value, magnitude.value))
    return None


def get_reaction(goal, relation, magnitude, esteem_tier):
    """Resolve a normalized body change into a symbolic buff and esteem delta."""
    if magnitude == Magnitude.NONE or not _goal_matches_relation(goal, relation):
        return FALLBACK

    profile = RULES.get((relation, magnitude, esteem_tier))
    if profile is None:
        return FALLBACK

    return Reaction(
        reaction_buff_key(goal, relation, magnitude, esteem_tier),
        profile.esteem_delta,
        profile.label,
    )
