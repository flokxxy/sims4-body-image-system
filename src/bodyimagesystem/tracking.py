"""Daily sampling and MVP reaction application."""

from bodyimagesystem import tuning
from bodyimagesystem.domain import (
    Axis,
    esteem_tier,
    direction_from_delta,
    magnitude_from_delta,
    relation_to_goal,
)
from bodyimagesystem.logger import log, log_exception
from bodyimagesystem.resolver import get_reaction
from bodyimagesystem import sims_api


SELF_ESTEEM_DEFAULT = 50
SNAPSHOT_UNSET = -999


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


def sample_sim(sim_info):
    """Run one daily sample for a sim and apply the highest-priority MVP reaction."""
    if not is_in_scope(sim_info):
        return

    try:
        if not ensure_initial_state(sim_info):
            log("Skipped sim; tuning statistics are missing or unavailable")
            return

        _sample_axis(sim_info, Axis.FAT, tuning.COMMODITY_FAT, tuning.STATISTIC_FAT_SNAPSHOT)
        _sample_axis(sim_info, Axis.FIT, tuning.COMMODITY_FIT, tuning.STATISTIC_FIT_SNAPSHOT)
    except Exception as exc:
        log_exception("Failed to sample sim", exc)


def _sample_axis(sim_info, axis, commodity_id, snapshot_id):
    current = sims_api.get_statistic_value(sim_info, commodity_id)
    previous = sims_api.get_statistic_value(sim_info, snapshot_id)
    if current is None or previous is None:
        return

    delta = current - previous
    sims_api.set_statistic_value(sim_info, snapshot_id, current)

    direction = direction_from_delta(delta)
    if direction is None:
        return

    focused = sims_api.has_trait(sim_info, tuning.TRAIT_APPEARANCE_FOCUSED)
    magnitude = magnitude_from_delta(delta, focused)
    goal = sims_api.current_goal(sim_info)
    relation = relation_to_goal(goal, axis, direction)
    tier = esteem_tier(
        sims_api.get_statistic_value(sim_info, tuning.STATISTIC_SELF_ESTEEM)
        or SELF_ESTEEM_DEFAULT
    )
    reaction = get_reaction(relation, magnitude, tier)

    if reaction.buff_id:
        sims_api.add_buff(sim_info, reaction.buff_id)
    if reaction.esteem_delta:
        sims_api.add_statistic_value(
            sim_info, tuning.STATISTIC_SELF_ESTEEM, reaction.esteem_delta
        )

    log(
        "sample axis={0} delta={1} goal={2} relation={3} magnitude={4} reaction={5}".format(
            axis.value,
            delta,
            goal.value,
            relation.value,
            magnitude.value,
            reaction.label,
        )
    )
