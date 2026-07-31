import unittest
from unittest import mock

from bodyimagesystem import tracking, tuning
from bodyimagesystem.domain import (
    Axis,
    EsteemTier,
    Goal,
    Magnitude,
    RelationToGoal,
)
from bodyimagesystem.resolver import Reaction
from bodyimagesystem.stagnation import (
    STAGNATION_ESTEEM_DELTA,
    StagnationStatus,
)


def make_sample(
    axis,
    delta,
    goal=Goal.MAINTAIN,
    relation=RelationToGoal.VIOLATION,
    magnitude=Magnitude.NOTICEABLE,
):
    return tracking.AxisSample(
        axis,
        delta,
        goal,
        relation,
        magnitude,
        Reaction("test.key", -1, "test"),
        -1,
    )


class TrackingTests(unittest.TestCase):
    def test_first_snapshot_creates_baseline_for_both_axes(self):
        sim_info = object()

        with mock.patch.object(
            tracking.sims_api,
            "get_statistic_value",
            side_effect=[50, 25, -10, -999, -999],
        ), mock.patch.object(
            tracking.sims_api,
            "set_statistic_value",
        ) as set_statistic_value:
            state = tracking.ensure_initial_state(sim_info)

        self.assertTrue(state.ready)
        self.assertTrue(state.baseline_created)
        self.assertEqual(
            set_statistic_value.call_args_list,
            [
                mock.call(sim_info, tuning.STATISTIC_FAT_SNAPSHOT, 25),
                mock.call(sim_info, tuning.STATISTIC_FIT_SNAPSHOT, -10),
            ],
        )

    def test_existing_snapshots_do_not_recreate_baseline(self):
        with mock.patch.object(
            tracking.sims_api,
            "get_statistic_value",
            side_effect=[50, 25, -10, 20, -8],
        ), mock.patch.object(
            tracking.sims_api,
            "set_statistic_value",
        ) as set_statistic_value:
            state = tracking.ensure_initial_state(object())

        self.assertTrue(state.ready)
        self.assertFalse(state.baseline_created)
        set_statistic_value.assert_not_called()

    def test_baseline_tick_skips_reactions_and_stagnation(self):
        sim_info = mock.Mock(is_selectable=True)

        with mock.patch.object(
            tracking,
            "ensure_initial_state",
            return_value=tracking.InitializationState(True, True),
        ), mock.patch.object(
            tracking,
            "_sampling_context",
        ) as sampling_context, mock.patch.object(
            tracking,
            "_update_stagnation",
        ) as update_stagnation:
            tracking.sample_sim(sim_info)

        sampling_context.assert_not_called()
        update_stagnation.assert_not_called()

    def test_zero_self_esteem_is_read_as_low_tier(self):
        sim_info = object()

        with mock.patch.object(
            tracking.sims_api,
            "get_statistic_value",
            return_value=0,
        ), mock.patch.object(
            tracking.sims_api,
            "has_trait",
            return_value=False,
        ), mock.patch.object(
            tracking.sims_api,
            "current_goal",
            return_value=Goal.GAIN_WEIGHT,
        ):
            context = tracking._sampling_context(sim_info)

        self.assertEqual(context.esteem_tier, EsteemTier.LOW)

    def test_appearance_focused_trait_amplifies_resolved_esteem_delta(self):
        sim_info = object()
        context = tracking.SamplingContext(
            Goal.GAIN_WEIGHT,
            EsteemTier.NEUTRAL,
            True,
        )

        with mock.patch.object(
            tracking.sims_api,
            "get_statistic_value",
            side_effect=[3, 0],
        ), mock.patch.object(
            tracking.sims_api,
            "set_statistic_value",
        ):
            sample = tracking._resolve_axis(
                sim_info,
                Axis.FAT,
                101,
                102,
                context,
            )

        self.assertEqual(
            sample.reaction.buff_key,
            "progress.gain_weight.neutral.noticeable",
        )
        self.assertEqual(sample.esteem_delta, 1.5)

    def test_missing_self_esteem_has_no_sampling_context(self):
        with mock.patch.object(
            tracking.sims_api,
            "get_statistic_value",
            return_value=None,
        ):
            context = tracking._sampling_context(object())

        self.assertIsNone(context)

    def test_apply_sample_maps_symbolic_key_to_tuning_id(self):
        sim_info = object()
        sample = make_sample(Axis.FAT, 8)

        with mock.patch.object(
            tracking.tuning,
            "reaction_buff_id",
            return_value=12345,
        ) as reaction_buff_id, mock.patch.object(
            tracking.sims_api,
            "add_buff",
        ) as add_buff, mock.patch.object(
            tracking.sims_api,
            "add_statistic_value",
        ) as add_statistic_value:
            tracking._apply_sample(sim_info, sample)

        reaction_buff_id.assert_called_once_with("test.key")
        add_buff.assert_called_once_with(sim_info, 12345)
        add_statistic_value.assert_called_once_with(
            sim_info,
            tuning.STATISTIC_SELF_ESTEEM,
            -1,
        )

    def test_maintain_tie_break_keeps_larger_absolute_change(self):
        smaller = make_sample(Axis.FAT, 6)
        larger = make_sample(Axis.FIT, -12)

        selected = tracking._select_samples_to_apply([smaller, larger])

        self.assertEqual(selected, [larger])

    def test_maintain_tie_break_is_deterministic_for_equal_changes(self):
        fat = make_sample(Axis.FAT, 8)
        fit = make_sample(Axis.FIT, -8)

        selected = tracking._select_samples_to_apply([fat, fit])

        self.assertEqual(selected, [fat])

    def test_non_violation_reactions_can_be_applied_together(self):
        progress = make_sample(
            Axis.FAT,
            -8,
            relation=RelationToGoal.PROGRESS,
        )
        irrelevant = make_sample(
            Axis.FIT,
            8,
            relation=RelationToGoal.IRRELEVANT,
        )

        selected = tracking._select_samples_to_apply([progress, irrelevant])

        self.assertEqual(selected, [progress, irrelevant])


class StagnationIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.sim_info = object()
        self.context = tracking.SamplingContext(
            Goal.GAIN_WEIGHT,
            EsteemTier.NEUTRAL,
            False,
        )

    def test_no_progress_increments_persisted_counter(self):
        with mock.patch.object(
            tracking.sims_api,
            "get_statistic_value",
            return_value=0,
        ), mock.patch.object(
            tracking.sims_api,
            "set_statistic_value",
        ) as set_statistic_value, mock.patch.object(
            tracking.sims_api,
            "add_buff",
        ) as add_buff, mock.patch.object(
            tracking.sims_api,
            "add_statistic_value",
        ) as add_statistic_value:
            update = tracking._update_stagnation(
                self.sim_info,
                self.context,
                [],
            )

        self.assertEqual(update.status, StagnationStatus.COUNTING)
        self.assertEqual(update.days_without_progress, 1)
        set_statistic_value.assert_called_once_with(
            self.sim_info,
            tuning.STATISTIC_STAGNATION_DAYS,
            1,
        )
        add_buff.assert_not_called()
        add_statistic_value.assert_not_called()

    def test_meaningful_progress_resets_persisted_counter(self):
        progress = make_sample(
            Axis.FAT,
            5,
            goal=Goal.GAIN_WEIGHT,
            relation=RelationToGoal.PROGRESS,
        )

        with mock.patch.object(
            tracking.sims_api,
            "get_statistic_value",
            return_value=2,
        ), mock.patch.object(
            tracking.sims_api,
            "set_statistic_value",
        ) as set_statistic_value, mock.patch.object(
            tracking.sims_api,
            "add_buff",
        ) as add_buff:
            update = tracking._update_stagnation(
                self.sim_info,
                self.context,
                [progress],
            )

        self.assertEqual(update.status, StagnationStatus.PROGRESS)
        set_statistic_value.assert_called_once_with(
            self.sim_info,
            tuning.STATISTIC_STAGNATION_DAYS,
            0,
        )
        add_buff.assert_not_called()

    def test_third_day_resets_counter_and_applies_stagnation_effect(self):
        with mock.patch.object(
            tracking.sims_api,
            "get_statistic_value",
            return_value=2,
        ), mock.patch.object(
            tracking.sims_api,
            "set_statistic_value",
        ) as set_statistic_value, mock.patch.object(
            tracking.sims_api,
            "add_buff",
        ) as add_buff, mock.patch.object(
            tracking.sims_api,
            "add_statistic_value",
        ) as add_statistic_value:
            update = tracking._update_stagnation(
                self.sim_info,
                self.context,
                [],
            )

        self.assertEqual(update.status, StagnationStatus.TRIGGERED)
        self.assertTrue(update.triggered)
        set_statistic_value.assert_called_once_with(
            self.sim_info,
            tuning.STATISTIC_STAGNATION_DAYS,
            0,
        )
        add_buff.assert_called_once_with(
            self.sim_info,
            tuning.BUFF_STAGNATION,
        )
        add_statistic_value.assert_called_once_with(
            self.sim_info,
            tuning.STATISTIC_SELF_ESTEEM,
            STAGNATION_ESTEEM_DELTA,
        )

    def test_paused_stagnation_preserves_counter(self):
        with mock.patch.object(
            tracking.sims_api,
            "get_statistic_value",
            return_value=2,
        ), mock.patch.object(
            tracking.sims_api,
            "set_statistic_value",
        ) as set_statistic_value, mock.patch.object(
            tracking.sims_api,
            "add_buff",
        ) as add_buff:
            update = tracking._update_stagnation(
                self.sim_info,
                self.context,
                [],
                paused=True,
            )

        self.assertEqual(update.status, StagnationStatus.PAUSED)
        self.assertEqual(update.days_without_progress, 2)
        set_statistic_value.assert_not_called()
        add_buff.assert_not_called()

    def test_missing_counter_skips_stagnation(self):
        with mock.patch.object(
            tracking.sims_api,
            "get_statistic_value",
            return_value=None,
        ), mock.patch.object(
            tracking.sims_api,
            "set_statistic_value",
        ) as set_statistic_value, mock.patch.object(
            tracking.sims_api,
            "add_buff",
        ) as add_buff:
            update = tracking._update_stagnation(
                self.sim_info,
                self.context,
                [],
            )

        self.assertIsNone(update)
        set_statistic_value.assert_not_called()
        add_buff.assert_not_called()


class TuningMappingTests(unittest.TestCase):
    def test_progress_key_uses_vertical_slice_buff_as_fallback(self):
        with mock.patch.object(tuning, "BUFF_TEST_PROGRESS", 987):
            self.assertEqual(
                tuning.reaction_buff_id(
                    "progress.lose_weight.low.noticeable"
                ),
                987,
            )

    def test_explicit_mapping_overrides_progress_fallback(self):
        with mock.patch.dict(
            tuning.REACTION_BUFF_IDS,
            {"progress.lose_weight.low.noticeable": 654},
            clear=True,
        ), mock.patch.object(tuning, "BUFF_TEST_PROGRESS", 987):
            self.assertEqual(
                tuning.reaction_buff_id(
                    "progress.lose_weight.low.noticeable"
                ),
                654,
            )


if __name__ == "__main__":
    unittest.main()
