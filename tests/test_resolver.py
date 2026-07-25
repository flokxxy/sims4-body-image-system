import unittest

from bodyimagesystem.domain import (
    Axis,
    Direction,
    EsteemTier,
    Goal,
    Magnitude,
    RelationToGoal,
    esteem_tier,
    magnitude_from_delta,
    relation_to_goal,
)
from bodyimagesystem.resolver import get_reaction


class ResolverTests(unittest.TestCase):
    def test_esteem_tiers(self):
        self.assertEqual(esteem_tier(30), EsteemTier.LOW)
        self.assertEqual(esteem_tier(31), EsteemTier.NEUTRAL)
        self.assertEqual(esteem_tier(70), EsteemTier.NEUTRAL)
        self.assertEqual(esteem_tier(71), EsteemTier.HIGH)

    def test_magnitude_thresholds_for_neutral_sim(self):
        self.assertEqual(magnitude_from_delta(4.9), Magnitude.NONE)
        self.assertEqual(magnitude_from_delta(5), Magnitude.NOTICEABLE)
        self.assertEqual(magnitude_from_delta(14.9), Magnitude.NOTICEABLE)
        self.assertEqual(magnitude_from_delta(15), Magnitude.SHARP)

    def test_magnitude_thresholds_for_appearance_focused_sim(self):
        self.assertEqual(
            magnitude_from_delta(2.4, appearance_focused=True), Magnitude.NONE
        )
        self.assertEqual(
            magnitude_from_delta(2.5, appearance_focused=True), Magnitude.NOTICEABLE
        )
        self.assertEqual(
            magnitude_from_delta(6.9, appearance_focused=True), Magnitude.NOTICEABLE
        )
        self.assertEqual(
            magnitude_from_delta(7, appearance_focused=True), Magnitude.SHARP
        )

    def test_goal_relation_for_weight_loss(self):
        self.assertEqual(
            relation_to_goal(Goal.LOSE_WEIGHT, Axis.FAT, Direction.DOWN),
            RelationToGoal.PROGRESS,
        )
        self.assertEqual(
            relation_to_goal(Goal.LOSE_WEIGHT, Axis.FAT, Direction.UP),
            RelationToGoal.REGRESS,
        )
        self.assertEqual(
            relation_to_goal(Goal.LOSE_WEIGHT, Axis.FIT, Direction.UP),
            RelationToGoal.IRRELEVANT,
        )

    def test_mvp_progress_reaction(self):
        reaction = get_reaction(
            RelationToGoal.PROGRESS, Magnitude.SHARP, EsteemTier.NEUTRAL
        )
        self.assertEqual(reaction.esteem_delta, 2)
        self.assertEqual(reaction.label, "confident")

    def test_unimplemented_resolver_cells_fall_back_to_neutral(self):
        reaction = get_reaction(
            RelationToGoal.REGRESS, Magnitude.NOTICEABLE, EsteemTier.NEUTRAL
        )
        self.assertIsNone(reaction.buff_id)
        self.assertEqual(reaction.esteem_delta, 0)


if __name__ == "__main__":
    unittest.main()
