"""Daily body sampling and reaction application."""

from collections import namedtuple

from bodyimagesystem import sims_api, tuning
from bodyimagesystem.domain import (
    Axis,
    Magnitude,
    RelationToGoal,
    adjusted_esteem_delta,
    direction_from_delta,
    esteem_tier,
    magnitude_from_delta,
    relation_to_goal,
)
from bodyimagesystem.logger import log, log_exception
from bodyimagesystem.resolver import get_reaction


SNAPSHOT_UNSET = -999

SamplingContext = namedtuple("SamplingContext", ("goal", "esteem_tier", "focused"))
AxisSample = namedtuple(
    "AxisSample",
    (
        "axis",
        "delta",
        "goal",
        "relation",
        "magnitude",
        "reaction",
        "esteem_delta",
    ),
)


def is_in_scope(sim_info):
    return getattr(sim_info, "is_selectable", False)


def ensure_initial_state(sim_info):
    """Seed custom statistics from current body values when first seen."""
    self_esteem = sims_api.get_statistic_value(sim_info, tuning.STATISTIC_SELF_ESTEEM)
    if self_esteem is None:
        return False

    fat = sims_api.get_statistic_value(sim_info, tuning.COMMODITY_FAT)
    fit = sims_api.get_statistic_value(sim_info, tuning.COMMODITY_FIT)
    if fat is None or fit is None:
        return False

    fat_snapshot = sims_api.get_statistic_value(sim_info, tuning.STATISTIC_FAT_SNAPSHOT)
    fit_snapshot = sims_api.get_statistic_value(sim_info, tuning.STATISTIC_FIT_SNAPSHOT)
    if fat_snapshot == SNAPSHOT_UNSET:
        sims_api.set_statistic_value(sim_info, tuning.STATISTIC_FAT_SNAPSHOT, fat)
    if fit_snapshot == SNAPSHOT_UNSET:
        sims_api.set_statistic_value(sim_info, tuning.STATISTIC_FIT_SNAPSHOT, fit)
    return True


def _sampling_context(sim_info):
    """Read reaction context once so both axes use the same daily state."""
    self_esteem = sims_api.get_statistic_value(
        sim_info, tuning.STATISTIC_SELF_ESTEEM
    )
    if self_esteem is None:
        return None

    return SamplingContext(
        sims_api.current_goal(sim_info),
        esteem_tier(self_esteem),
        sims_api.has_trait(sim_info, tuning.TRAIT_APPEARANCE_FOCUSED),
    )


def sample_sim(sim_info):
    """Run one daily sample and apply the selected reactions for both axes."""
    if not is_in_scope(sim_info):
        return

    try:
        if not ensure_initial_state(sim_info):
            log("Skipped sim; tuning statistics are missing or unavailable")
            return

        context = _sampling_context(sim_info)
        if context is None:
            log("Skipped sim; self-esteem statistic is unavailable")
            return

        samples = [
            _resolve_axis(
                sim_info,
                Axis.FAT,
                tuning.COMMODITY_FAT,
                tuning.STATISTIC_FAT_SNAPSHOT,
                context,
            ),
            _resolve_axis(
                sim_info,
                Axis.FIT,
                tuning.COMMODITY_FIT,
                tuning.STATISTIC_FIT_SNAPSHOT,
                context,
            ),
        ]
        samples = [sample for sample in samples if sample is not None]
        selected = _select_samples_to_apply(samples)
        selected_ids = {id(sample) for sample in selected}

        for sample in samples:
            if id(sample) in selected_ids:
                _apply_sample(sim_info, sample)
            else:
                log(
                    "suppressed axis={0} delta={1} relation={2} reason=maintain_tie_break"
                    .format(
                        sample.axis.value,
                        sample.delta,
                        sample.relation.value,
                    )
                )
    except Exception as exc:
        log_exception("Failed to sample sim", exc)


def _resolve_axis(sim_info, axis, commodity_id, snapshot_id, context):
    current = sims_api.get_statistic_value(sim_info, commodity_id)
    previous = sims_api.get_statistic_value(sim_info, snapshot_id)
    if current is None or previous is None:
        return None

    delta = current - previous
    sims_api.set_statistic_value(sim_info, snapshot_id, current)

    direction = direction_from_delta(delta)
    if direction is None:
        return None

    magnitude = magnitude_from_delta(delta, context.focused)
    relation = relation_to_goal(context.goal, axis, direction)
    reaction = get_reaction(
        context.goal,
        relation,
        magnitude,
        context.esteem_tier,
    )

    return AxisSample(
        axis,
        delta,
        context.goal,
        relation,
        magnitude,
        reaction,
        adjusted_esteem_delta(reaction.esteem_delta, context.focused),
    )


def _select_samples_to_apply(samples):
    """Apply only the larger MAINTAIN violation when both axes changed."""
    violations = [
        sample
        for sample in samples
        if sample.relation == RelationToGoal.VIOLATION
        and sample.magnitude != Magnitude.NONE
    ]
    if len(violations) < 2:
        return list(samples)

    winner = max(violations, key=lambda sample: abs(sample.delta))
    return [
        sample
        for sample in samples
        if sample.relation != RelationToGoal.VIOLATION or sample is winner
    ]


def _apply_sample(sim_info, sample):
    buff_id = tuning.reaction_buff_id(sample.reaction.buff_key)
    if buff_id:
        sims_api.add_buff(sim_info, buff_id)
    if sample.esteem_delta:
        sims_api.add_statistic_value(
            sim_info,
            tuning.STATISTIC_SELF_ESTEEM,
            sample.esteem_delta,
        )

    log(
        "sample axis={0} delta={1} goal={2} relation={3} magnitude={4} "
        "reaction={5} buff_key={6} esteem_delta={7}".format(
            sample.axis.value,
            sample.delta,
            sample.goal.value,
            sample.relation.value,
            sample.magnitude.value,
            sample.reaction.label,
            sample.reaction.buff_key,
            sample.esteem_delta,
        )
    )
