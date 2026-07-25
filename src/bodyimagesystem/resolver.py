"""Reaction resolver for daily body changes.

This module deliberately avoids Sims imports so the rule table can be tested
without launching the game.
"""

from collections import namedtuple

from bodyimagesystem.domain import (
    EsteemTier,
    Magnitude,
    RelationToGoal,
)
from bodyimagesystem import tuning


Reaction = namedtuple("Reaction", ("buff_id", "esteem_delta", "label"))

FALLBACK = Reaction(None, 0, "neutral")


RULES = {
    # MVP rule. Once tuning resources exist, this table can be expanded to the
    # full 50-buff catalog from the specification.
    (RelationToGoal.PROGRESS, Magnitude.NOTICEABLE, EsteemTier.LOW): Reaction(
        tuning.BUFF_TEST_PROGRESS, 1, "slightly_encouraged"
    ),
    (RelationToGoal.PROGRESS, Magnitude.NOTICEABLE, EsteemTier.NEUTRAL): Reaction(
        tuning.BUFF_TEST_PROGRESS, 1, "pleased"
    ),
    (RelationToGoal.PROGRESS, Magnitude.NOTICEABLE, EsteemTier.HIGH): Reaction(
        tuning.BUFF_TEST_PROGRESS, 1, "confident"
    ),
    (RelationToGoal.PROGRESS, Magnitude.SHARP, EsteemTier.LOW): Reaction(
        tuning.BUFF_TEST_PROGRESS, 2, "inspired"
    ),
    (RelationToGoal.PROGRESS, Magnitude.SHARP, EsteemTier.NEUTRAL): Reaction(
        tuning.BUFF_TEST_PROGRESS, 2, "confident"
    ),
    (RelationToGoal.PROGRESS, Magnitude.SHARP, EsteemTier.HIGH): Reaction(
        tuning.BUFF_TEST_PROGRESS, 2, "proud"
    ),
}


def get_reaction(relation, magnitude, esteem_tier):
    if magnitude == Magnitude.NONE:
        return FALLBACK
    return RULES.get((relation, magnitude, esteem_tier), FALLBACK)

