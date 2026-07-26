import unittest

from bodyimagesystem.domain import Goal
from bodyimagesystem.stagnation import (
    STAGNATION_DAYS_REQUIRED,
    StagnationStatus,
    advance_stagnation,
    has_meaningful_progress,
    progress_delta_for_goal,
)


class GoalProgressTests(unittest.TestCase):
    def test_progress_delta_uses_the_correct_axis_and_direction(self):
        self.assertEqual(progress_delta_for_goal(Goal.LOSE_WEIGHT, -6, 20), 6)
        self.assertEqual(progress_delta_for_goal(Goal.GAIN_WEIGHT, 6, -20), 6)
        self.assertEqual(progress_delta_for_goal(Goal.GAIN_MUSCLE, -20, 6), 6)

    def test_non_directed_goals_have_no_progress_axis(self):
        self.assertIsNone(progress_delta_for_goal(Goal.MAINTAIN, 10, 10))
        self.assertIsNone(progress_delta_for_goal(Goal.NONE, 10, 10))

    def test_wrong_direction_is_not_progress(self):
        self.assertFalse(
            has_meaningful_progress(Goal.LOSE_WEIGHT, 6, 0)
        )
        self.assertFalse(
            has_meaningful_progress(Goal.GAIN_WEIGHT, -6, 0)
        )
        self.assertFalse(
            has_meaningful_progress(Goal.GAIN_MUSCLE, 0, -6)
        )

    def test_unrelated_axis_does_not_count_as_progress(self):
        self.assertFalse(
            has_meaningful_progress(Goal.LOSE_WEIGHT, 0, 20)
        )
        self.assertFalse(
            has_meaningful_progress(Goal.GAIN_MUSCLE, -20, 0)
        )

    def test_progress_uses_normal_and_appearance_focused_thresholds(self):
        self.assertFalse(
            has_meaningful_progress(Goal.GAIN_WEIGHT, 3, 0)
        )
        self.assertTrue(
            has_meaningful_progress(
                Goal.GAIN_WEIGHT,
                3,
                0,
                appearance_focused=True,
            )
        )


class StagnationStateMachineTests(unittest.TestCase):
    def test_meaningful_progress_resets_counter(self):
        update = advance_stagnation(
            2,
            Goal.LOSE_WEIGHT,
            fat_delta=-5,
            fit_delta=0,
        )

        self.assertEqual(update.days_without_progress, 0)
        self.assertFalse(update.triggered)
        self.assertEqual(update.status, StagnationStatus.PROGRESS)

    def test_subthreshold_progress_increments_counter(self):
        update = advance_stagnation(
            0,
            Goal.LOSE_WEIGHT,
            fat_delta=-4.9,
            fit_delta=0,
        )

        self.assertEqual(update.days_without_progress, 1)
        self.assertFalse(update.triggered)
        self.assertEqual(update.status, StagnationStatus.COUNTING)

    def test_regress_increments_counter(self):
        update = advance_stagnation(
            1,
            Goal.LOSE_WEIGHT,
            fat_delta=10,
            fit_delta=0,
        )

        self.assertEqual(update.days_without_progress, 2)
        self.assertFalse(update.triggered)
        self.assertEqual(update.status, StagnationStatus.COUNTING)

    def test_third_day_triggers_and_resets_counter(self):
        update = advance_stagnation(
            STAGNATION_DAYS_REQUIRED - 1,
            Goal.GAIN_MUSCLE,
            fat_delta=0,
            fit_delta=0,
        )

        self.assertEqual(update.days_without_progress, 0)
        self.assertTrue(update.triggered)
        self.assertEqual(update.status, StagnationStatus.TRIGGERED)

    def test_stagnation_can_trigger_again_after_another_full_cycle(self):
        days = 0
        triggers = 0

        for _ in range(STAGNATION_DAYS_REQUIRED * 2):
            update = advance_stagnation(
                days,
                Goal.GAIN_WEIGHT,
                fat_delta=0,
                fit_delta=0,
            )
            days = update.days_without_progress
            triggers += int(update.triggered)

        self.assertEqual(triggers, 2)
        self.assertEqual(days, 0)

    def test_pause_preserves_counter_without_triggering(self):
        update = advance_stagnation(
            2,
            Goal.LOSE_WEIGHT,
            fat_delta=20,
            fit_delta=-20,
            paused=True,
        )

        self.assertEqual(update.days_without_progress, 2)
        self.assertFalse(update.triggered)
        self.assertEqual(update.status, StagnationStatus.PAUSED)

    def test_non_directed_goal_clears_counter(self):
        for goal in (Goal.MAINTAIN, Goal.NONE):
            with self.subTest(goal=goal):
                update = advance_stagnation(
                    2,
                    goal,
                    fat_delta=0,
                    fit_delta=0,
                )

                self.assertEqual(update.days_without_progress, 0)
                self.assertFalse(update.triggered)
                self.assertEqual(
                    update.status,
                    StagnationStatus.NOT_APPLICABLE,
                )

    def test_negative_persisted_counter_is_normalized(self):
        update = advance_stagnation(
            -10,
            Goal.GAIN_WEIGHT,
            fat_delta=0,
            fit_delta=0,
        )

        self.assertEqual(update.days_without_progress, 1)


if __name__ == "__main__":
    unittest.main()
