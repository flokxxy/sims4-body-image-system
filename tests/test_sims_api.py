import unittest
import sys
import types
from unittest import mock

from bodyimagesystem import sims_api, tuning
from bodyimagesystem.domain import Goal


class TuningResourceIdTests(unittest.TestCase):
    def test_body_commodity_ids_match_the_ea_reference_exports(self):
        self.assertEqual(tuning.COMMODITY_FAT, 0x00000000000040CD)
        self.assertEqual(tuning.COMMODITY_FIT, 0x00000000000040CE)

    def test_statistic_ids_match_the_package_resource_index(self):
        self.assertEqual(
            tuning.STATISTIC_SELF_ESTEEM,
            0x00000000CDE0665B,
        )
        self.assertEqual(
            tuning.STATISTIC_FAT_SNAPSHOT,
            0x00000000AE7D61F7,
        )
        self.assertEqual(
            tuning.STATISTIC_FIT_SNAPSHOT,
            0x000000008926D7AF,
        )
        self.assertEqual(
            tuning.STATISTIC_STAGNATION_DAYS,
            0x00000000CE0CDD56,
        )
        self.assertEqual(
            tuning.STATISTIC_GOAL_ACHIEVED_FLAG,
            0x00000000C06C893C,
        )

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

    def test_buff_ids_match_the_package_resource_index(self):
        self.assertEqual(tuning.BUFF_TEST_PROGRESS, 0x00000000C0F3A961)
        self.assertEqual(tuning.BUFF_STAGNATION, 0x00000000EE3B5EF1)


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


class SetGoalTests(unittest.TestCase):
    def setUp(self):
        self.traits = {
            trait_id: "trait-{0}".format(goal.value)
            for trait_id, goal in sims_api.GOAL_TRAIT_PRIORITY
        }
        self.active_traits = {
            self.traits[tuning.TRAIT_GOAL_GAIN_WEIGHT],
            self.traits[tuning.TRAIT_GOAL_MAINTAIN],
        }
        self.tracker = types.SimpleNamespace(
            has_trait=lambda trait_type: trait_type in self.active_traits,
            add_trait=lambda trait_type: self.active_traits.add(trait_type),
            remove_trait=lambda trait_type: self.active_traits.remove(trait_type),
        )
        self.sim_info = types.SimpleNamespace(trait_tracker=self.tracker)

        resources = types.ModuleType("sims4.resources")
        resources.Types = types.SimpleNamespace(TRAIT="TRAIT")
        sims4 = types.ModuleType("sims4")
        sims4.resources = resources
        self.module_patch = mock.patch.dict(
            sys.modules,
            {"sims4": sims4, "sims4.resources": resources},
        )
        self.module_patch.start()

    def tearDown(self):
        self.module_patch.stop()

    def test_set_goal_removes_conflicts_and_adds_selected_trait(self):
        with mock.patch.object(
            sims_api,
            "get_tuned_instance",
            side_effect=lambda _resource_type, trait_id: self.traits[trait_id],
        ):
            result = sims_api.set_goal(self.sim_info, Goal.LOSE_WEIGHT)

        self.assertTrue(result)
        self.assertEqual(
            self.active_traits,
            {self.traits[tuning.TRAIT_GOAL_LOSE_WEIGHT]},
        )

    def test_none_removes_every_goal_trait(self):
        with mock.patch.object(
            sims_api,
            "get_tuned_instance",
            side_effect=lambda _resource_type, trait_id: self.traits[trait_id],
        ):
            result = sims_api.set_goal(self.sim_info, Goal.NONE)

        self.assertTrue(result)
        self.assertEqual(self.active_traits, set())

    def test_missing_tuning_does_not_modify_existing_traits(self):
        before = set(self.active_traits)
        with mock.patch.object(
            sims_api,
            "get_tuned_instance",
            return_value=None,
        ):
            result = sims_api.set_goal(self.sim_info, Goal.LOSE_WEIGHT)

        self.assertFalse(result)
        self.assertEqual(self.active_traits, before)


if __name__ == "__main__":
    unittest.main()
