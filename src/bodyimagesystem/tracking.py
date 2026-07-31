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
from bodyimagesystem.stagnation import (
    STAGNATION_ESTEEM_DELTA,
    advance_stagnation,
)


SNAPSHOT_UNSET = -999

InitializationState = namedtuple(
    "InitializationState",
    ("ready", "baseline_created"),
)
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
    """Seed body baselines and report whether this is the first sample."""
    self_esteem = sims_api.get_statistic_value(sim_info, tuning.STATISTIC_SELF_ESTEEM)
    if self_esteem is None:
        return InitializationState(False, False)

    fat = sims_api.get_statistic_value(sim_info, tuning.COMMODITY_FAT)
    fit = sims_api.get_statistic_value(sim_info, tuning.COMMODITY_FIT)
    if fat is None or fit is None:
        return InitializationState(False, False)

    fat_snapshot = sims_api.get_statistic_value(sim_info, tuning.STATISTIC_FAT_SNAPSHOT)
    fit_snapshot = sims_api.get_statistic_value(sim_info, tuning.STATISTIC_FIT_SNAPSHOT)
    baseline_created = False
    if fat_snapshot == SNAPSHOT_UNSET:
        sims_api.set_statistic_value(sim_info, tuning.STATISTIC_FAT_SNAPSHOT, fat)
        baseline_created = True
    if fit_snapshot == SNAPSHOT_UNSET:
        sims_api.set_statistic_value(sim_info, tuning.STATISTIC_FIT_SNAPSHOT, fit)
        baseline_created = True
    return InitializationState(True, baseline_created)


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
        initialization = ensure_initial_state(sim_info)
        if not initialization.ready:
            log("Skipped sim; tuning statistics are missing or unavailable")
            return
        if initialization.baseline_created:
            log("Initialized body snapshot baseline; reactions start next window")
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

        _update_stagnation(sim_info, context, samples)
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


def _axis_delta(samples, axis):
    for sample in samples:
        if sample.axis == axis:
            return sample.delta
    return 0


def _update_stagnation(sim_info, context, samples, paused=False):
    """Persist one daily stagnation transition and apply its trigger effect."""
    current_days = sims_api.get_statistic_value(
        sim_info,
        tuning.STATISTIC_STAGNATION_DAYS,
    )
    if current_days is None:
        log("Skipped stagnation; counter statistic is unavailable")
        return None

    update = advance_stagnation(
        current_days,
        context.goal,
        _axis_delta(samples, Axis.FAT),
        _axis_delta(samples, Axis.FIT),
        appearance_focused=context.focused,
        paused=paused,
    )

    if update.days_without_progress != current_days:
        sims_api.set_statistic_value(
            sim_info,
            tuning.STATISTIC_STAGNATION_DAYS,
            update.days_without_progress,
        )

    if update.triggered:
        sims_api.add_buff(sim_info, tuning.BUFF_STAGNATION)
        sims_api.add_statistic_value(
            sim_info,
            tuning.STATISTIC_SELF_ESTEEM,
            STAGNATION_ESTEEM_DELTA,
        )

    log(
        "stagnation goal={0} status={1} days={2} triggered={3}".format(
            context.goal.value,
            update.status.value,
            update.days_without_progress,
            update.triggered,
        )
    )
    return update
