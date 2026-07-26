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


def make_sample(
    axis,
    delta,
    relation=RelationToGoal.VIOLATION,
    magnitude=Magnitude.NOTICEABLE,
):
    return tracking.AxisSample(
        axis,
        delta,
        Goal.MAINTAIN,
        relation,
        magnitude,
        Reaction("test.key", -1, "test"),
        -1,
    )


class TrackingTests(unittest.TestCase):
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
