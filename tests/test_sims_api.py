import unittest
from unittest import mock

from bodyimagesystem import sims_api, tuning
from bodyimagesystem.domain import Goal


class TuningTraitIdTests(unittest.TestCase):
    def test_trait_ids_match_the_package_resource_index(self):
        self.assertEqual(
            tuning.TRAIT_APPEARANCE_FOCUSED,
            0x00000000D4BB0699,
        )
        self.assertEqual(
            tuning.TRAIT_GOAL_LOSE_WEIGHT,
            0x0000000080A37607,
        )
        self.assertEqual(
            tuning.TRAIT_GOAL_GAIN_WEIGHT,
            0x00000000E82B728D,
        )
        self.assertEqual(
            tuning.TRAIT_GOAL_GAIN_MUSCLE,
            0x00000000C37BC038,
        )
        self.assertEqual(
            tuning.TRAIT_GOAL_MAINTAIN,
            0x00000000C1D975C3,
        )


class CurrentGoalTests(unittest.TestCase):
    def test_each_goal_trait_is_recognized(self):
        cases = (
            (tuning.TRAIT_GOAL_LOSE_WEIGHT, Goal.LOSE_WEIGHT),
            (tuning.TRAIT_GOAL_GAIN_WEIGHT, Goal.GAIN_WEIGHT),
            (tuning.TRAIT_GOAL_GAIN_MUSCLE, Goal.GAIN_MUSCLE),
            (tuning.TRAIT_GOAL_MAINTAIN, Goal.MAINTAIN),
        )

        for active_trait_id, expected_goal in cases:
            with self.subTest(goal=expected_goal), mock.patch.object(
                sims_api,
                "has_trait",
                side_effect=lambda _sim, trait_id: trait_id == active_trait_id,
            ):
                self.assertEqual(
                    sims_api.current_goal(object()),
                    expected_goal,
                )

    def test_no_goal_trait_returns_none(self):
        with mock.patch.object(
            sims_api,
            "has_trait",
            return_value=False,
        ):
            self.assertEqual(sims_api.current_goal(object()), Goal.NONE)

    def test_multiple_goal_traits_use_documented_priority(self):
        active_traits = {
            tuning.TRAIT_GOAL_GAIN_WEIGHT,
            tuning.TRAIT_GOAL_MAINTAIN,
        }

        with mock.patch.object(
            sims_api,
            "has_trait",
            side_effect=lambda _sim, trait_id: trait_id in active_traits,
        ):
            self.assertEqual(
                sims_api.current_goal(object()),
                Goal.GAIN_WEIGHT,
            )

    def test_priority_covers_every_goal_exactly_once(self):
        trait_ids = [item[0] for item in sims_api.GOAL_TRAIT_PRIORITY]
        goals = [item[1] for item in sims_api.GOAL_TRAIT_PRIORITY]

        self.assertEqual(len(trait_ids), len(set(trait_ids)))
        self.assertEqual(
            set(goals),
            {
                Goal.LOSE_WEIGHT,
                Goal.GAIN_WEIGHT,
                Goal.GAIN_MUSCLE,
                Goal.MAINTAIN,
            },
        )


if __name__ == "__main__":
    unittest.main()
