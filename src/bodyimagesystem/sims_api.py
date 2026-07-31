"""Thin Sims 4 API wrappers.

The concrete imports and manager constants should be verified against the
decompiled scripts for the current game patch before playtesting.
"""

from bodyimagesystem import tuning
from bodyimagesystem.domain import Goal


GOAL_TRAIT_PRIORITY = (
    (tuning.TRAIT_GOAL_LOSE_WEIGHT, Goal.LOSE_WEIGHT),
    (tuning.TRAIT_GOAL_GAIN_WEIGHT, Goal.GAIN_WEIGHT),
    (tuning.TRAIT_GOAL_GAIN_MUSCLE, Goal.GAIN_MUSCLE),
    (tuning.TRAIT_GOAL_MAINTAIN, Goal.MAINTAIN),
)

GOAL_TRAIT_IDS = {
    goal: trait_id for trait_id, goal in GOAL_TRAIT_PRIORITY
}


def get_instance_manager(resource_type):
    import services

    return services.get_instance_manager(resource_type)


def get_tuned_instance(resource_type, instance_id):
    manager = get_instance_manager(resource_type)
    if manager is None:
        return None
    return manager.get(instance_id)


def get_statistic_value(sim_info, statistic_id):
    from sims4.resources import Types

    statistic_type = get_tuned_instance(Types.STATISTIC, statistic_id)
    if statistic_type is None:
        return None

    tracker = sim_info.commodity_tracker
    statistic = tracker.get_statistic(statistic_type, add=True)
    if statistic is None:
        return None
    return statistic.get_value()


def set_statistic_value(sim_info, statistic_id, value):
    from sims4.resources import Types

    statistic_type = get_tuned_instance(Types.STATISTIC, statistic_id)
    if statistic_type is None:
        return False

    tracker = sim_info.commodity_tracker
    statistic = tracker.get_statistic(statistic_type, add=True)
    if statistic is None:
        return False
    statistic.set_value(value)
    return True


def add_statistic_value(sim_info, statistic_id, delta):
    current = get_statistic_value(sim_info, statistic_id)
    if current is None:
        return False
    return set_statistic_value(sim_info, statistic_id, current + delta)


def add_buff(sim_info, buff_id):
    from sims4.resources import Types

    buff_type = get_tuned_instance(Types.BUFF, buff_id)
    if buff_type is None:
        return False
    sim_info.Buffs.add_buff(buff_type)
    return True


def has_trait(sim_info, trait_id):
    from sims4.resources import Types

    trait_type = get_tuned_instance(Types.TRAIT, trait_id)
    if trait_type is None:
        return False
    return sim_info.trait_tracker.has_trait(trait_type)


def _add_trait(sim_info, trait_type):
    """Add a trait across the SimInfo API variants used by game patches."""
    add_trait = getattr(sim_info, "add_trait", None)
    if add_trait is not None:
        add_trait(trait_type)
        return
    sim_info.trait_tracker.add_trait(trait_type)


def _remove_trait(sim_info, trait_type):
    """Remove a trait across the SimInfo API variants used by game patches."""
    remove_trait = getattr(sim_info, "remove_trait", None)
    if remove_trait is not None:
        remove_trait(trait_type)
        return
    sim_info.trait_tracker.remove_trait(trait_type)


def set_goal(sim_info, goal):
    """Replace all body-goal traits with the selected goal.

    ``Goal.NONE`` means that every body-goal trait is removed. All tuning
    resources are resolved before making changes so a missing resource cannot
    leave the Sim with a partially changed goal state.
    """
    from sims4.resources import Types

    if not isinstance(goal, Goal):
        return False

    resolved_traits = []
    for trait_id, configured_goal in GOAL_TRAIT_PRIORITY:
        trait_type = get_tuned_instance(Types.TRAIT, trait_id)
        if trait_type is None:
            return False
        resolved_traits.append((trait_type, configured_goal))

    for trait_type, _configured_goal in resolved_traits:
        if sim_info.trait_tracker.has_trait(trait_type):
            _remove_trait(sim_info, trait_type)

    if goal != Goal.NONE:
        for trait_type, configured_goal in resolved_traits:
            if configured_goal == goal:
                _add_trait(sim_info, trait_type)
                break
    return True


def current_goal(sim_info):
    """Return the active body goal, with deterministic conflict handling.

    Goal-setting code must keep these traits mutually exclusive. The explicit
    priority is only a defensive fallback for saves containing multiple goals.
    """
    for trait_id, goal in GOAL_TRAIT_PRIORITY:
        if has_trait(sim_info, trait_id):
            return goal
    return Goal.NONE
