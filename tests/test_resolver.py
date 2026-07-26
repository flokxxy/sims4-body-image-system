import unittest

from bodyimagesystem.domain import (
    Axis,
    Direction,
    EsteemTier,
    Goal,
    Magnitude,
    RelationToGoal,
    adjusted_esteem_delta,
    esteem_tier,
    magnitude_from_delta,
    relation_to_goal,
)
from bodyimagesystem.resolver import (
    DIRECTED_GOALS,
    FALLBACK,
    RULES,
    get_reaction,
)


EXPECTED_REACTIONS = {
    RelationToGoal.PROGRESS: {
        EsteemTier.LOW: {
            Magnitude.NOTICEABLE: ("slightly_encouraged", 1),
            Magnitude.SHARP: ("inspired", 2),
        },
        EsteemTier.NEUTRAL: {
            Magnitude.NOTICEABLE: ("pleased", 1),
            Magnitude.SHARP: ("confident", 2),
        },
        EsteemTier.HIGH: {
            Magnitude.NOTICEABLE: ("confident", 1),
            Magnitude.SHARP: ("proud", 2),
        },
    },
    RelationToGoal.REGRESS: {
        EsteemTier.LOW: {
            Magnitude.NOTICEABLE: ("worried", -1),
            Magnitude.SHARP: ("depressed", -3),
        },
        EsteemTier.NEUTRAL: {
            Magnitude.NOTICEABLE: ("upset", -1),
            Magnitude.SHARP: ("worried", -2),
        },
        EsteemTier.HIGH: {
            Magnitude.NOTICEABLE: ("slightly_hurt", -1),
            Magnitude.SHARP: ("upset", -1),
        },
    },
    RelationToGoal.VIOLATION: {
        EsteemTier.LOW: {
            Magnitude.NOTICEABLE: ("tense", -1),
            Magnitude.SHARP: ("worried", -2),
        },
        EsteemTier.NEUTRAL: {
            Magnitude.NOTICEABLE: ("slightly_tense", -1),
            Magnitude.SHARP: ("tense", -1),
        },
        EsteemTier.HIGH: {
            Magnitude.NOTICEABLE: ("neutral", 0),
            Magnitude.SHARP: ("slightly_worried", -1),
        },
    },
    RelationToGoal.NO_GOAL: {
        EsteemTier.LOW: {
            Magnitude.NOTICEABLE: ("uneasy", -1),
            Magnitude.SHARP: ("pensive_uneasy", -1),
        },
        EsteemTier.NEUTRAL: {
            Magnitude.NOTICEABLE: ("neutral", 0),
            Magnitude.SHARP: ("pensive", 0),
        },
        EsteemTier.HIGH: {
            Magnitude.NOTICEABLE: ("neutral", 0),
            Magnitude.SHARP: ("calm_acceptance", 1),
        },
    },
    RelationToGoal.IRRELEVANT: {
        EsteemTier.LOW: {
            Magnitude.NOTICEABLE: ("neutral", 0),
            Magnitude.SHARP: ("pleasantly_surprised", 1),
        },
        EsteemTier.NEUTRAL: {
            Magnitude.NOTICEABLE: ("neutral", 0),
            Magnitude.SHARP: ("pleasantly_surprised", 1),
        },
        EsteemTier.HIGH: {
            Magnitude.NOTICEABLE: ("neutral", 0),
            Magnitude.SHARP: ("pleasantly_surprised", 1),
        },
    },
}


GOAL_FOR_RELATION = {
    RelationToGoal.PROGRESS: Goal.LOSE_WEIGHT,
    RelationToGoal.REGRESS: Goal.LOSE_WEIGHT,
    RelationToGoal.VIOLATION: Goal.MAINTAIN,
    RelationToGoal.NO_GOAL: Goal.NONE,
    RelationToGoal.IRRELEVANT: Goal.LOSE_WEIGHT,
}


class DomainTests(unittest.TestCase):
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
            magnitude_from_delta(2.5, appearance_focused=True),
            Magnitude.NOTICEABLE,
        )
        self.assertEqual(
            magnitude_from_delta(6.9, appearance_focused=True),
            Magnitude.NOTICEABLE,
        )
        self.assertEqual(
            magnitude_from_delta(7, appearance_focused=True), Magnitude.SHARP
        )

    def test_appearance_focused_trait_amplifies_positive_and_negative_deltas(self):
        self.assertEqual(adjusted_esteem_delta(2), 2)
        self.assertEqual(adjusted_esteem_delta(2, appearance_focused=True), 3)
        self.assertEqual(adjusted_esteem_delta(-2, appearance_focused=True), -3)

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


class ResolverTests(unittest.TestCase):
    def test_complete_thirty_cell_rule_matrix(self):
        self.assertEqual(len(RULES), 30)

        checked = 0
        for relation, tiers in EXPECTED_REACTIONS.items():
            goal = GOAL_FOR_RELATION[relation]
            for tier, magnitudes in tiers.items():
                for magnitude, expected in magnitudes.items():
                    with self.subTest(
                        relation=relation,
                        tier=tier,
                        magnitude=magnitude,
                    ):
                        reaction = get_reaction(goal, relation, magnitude, tier)
                        self.assertEqual(reaction.label, expected[0])
                        self.assertEqual(reaction.esteem_delta, expected[1])
                        self.assertIsNotNone(reaction.buff_key)
                    checked += 1

        self.assertEqual(checked, 30)

    def test_progress_and_regress_keys_include_the_specific_goal(self):
        weight_loss = get_reaction(
            Goal.LOSE_WEIGHT,
            RelationToGoal.PROGRESS,
            Magnitude.NOTICEABLE,
            EsteemTier.LOW,
        )
        muscle_gain = get_reaction(
            Goal.GAIN_MUSCLE,
            RelationToGoal.PROGRESS,
            Magnitude.NOTICEABLE,
            EsteemTier.LOW,
        )

        self.assertEqual(
            weight_loss.buff_key,
            "progress.lose_weight.low.noticeable",
        )
        self.assertEqual(
            muscle_gain.buff_key,
            "progress.gain_muscle.low.noticeable",
        )
        self.assertNotEqual(weight_loss.buff_key, muscle_gain.buff_key)

    def test_irrelevant_key_does_not_split_by_goal_or_tier(self):
        low = get_reaction(
            Goal.LOSE_WEIGHT,
            RelationToGoal.IRRELEVANT,
            Magnitude.SHARP,
            EsteemTier.LOW,
        )
        high = get_reaction(
            Goal.GAIN_MUSCLE,
            RelationToGoal.IRRELEVANT,
            Magnitude.SHARP,
            EsteemTier.HIGH,
        )

        self.assertEqual(low.buff_key, "irrelevant.sharp")
        self.assertEqual(high.buff_key, low.buff_key)

    def test_symbolic_catalog_has_fifty_unique_buff_keys(self):
        keys = set()
        for relation in (RelationToGoal.PROGRESS, RelationToGoal.REGRESS):
            for goal in DIRECTED_GOALS:
                for tier in EsteemTier:
                    for magnitude in (Magnitude.NOTICEABLE, Magnitude.SHARP):
                        keys.add(
                            get_reaction(
                                goal,
                                relation,
                                magnitude,
                                tier,
                            ).buff_key
                        )

        for relation, goal in (
            (RelationToGoal.VIOLATION, Goal.MAINTAIN),
            (RelationToGoal.NO_GOAL, Goal.NONE),
        ):
            for tier in EsteemTier:
                for magnitude in (Magnitude.NOTICEABLE, Magnitude.SHARP):
                    keys.add(
                        get_reaction(
                            goal,
                            relation,
                            magnitude,
                            tier,
                        ).buff_key
                    )

        for magnitude in (Magnitude.NOTICEABLE, Magnitude.SHARP):
            keys.add(
                get_reaction(
                    Goal.LOSE_WEIGHT,
                    RelationToGoal.IRRELEVANT,
                    magnitude,
                    EsteemTier.NEUTRAL,
                ).buff_key
            )

        self.assertEqual(len(keys), 50)
        self.assertNotIn(None, keys)

    def test_none_magnitude_falls_back(self):
        reaction = get_reaction(
            Goal.LOSE_WEIGHT,
            RelationToGoal.PROGRESS,
            Magnitude.NONE,
            EsteemTier.NEUTRAL,
        )
        self.assertEqual(reaction, FALLBACK)

    def test_inconsistent_goal_and_relation_fall_back(self):
        reaction = get_reaction(
            Goal.NONE,
            RelationToGoal.PROGRESS,
            Magnitude.SHARP,
            EsteemTier.NEUTRAL,
        )
        self.assertEqual(reaction, FALLBACK)


if __name__ == "__main__":
    unittest.main()
