"""Thin Sims 4 API wrappers.

The concrete imports and manager constants should be verified against the
decompiled scripts for the current game patch before playtesting.
"""

from bodyimagesystem import tuning
from bodyimagesystem.domain import Goal


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


def current_goal(sim_info):
    if has_trait(sim_info, tuning.TRAIT_GOAL_LOSE_WEIGHT):
        return Goal.LOSE_WEIGHT
    if has_trait(sim_info, tuning.TRAIT_GOAL_GAIN_WEIGHT):
        return Goal.GAIN_WEIGHT
    if has_trait(sim_info, tuning.TRAIT_GOAL_GAIN_MUSCLE):
        return Goal.GAIN_MUSCLE
    if has_trait(sim_info, tuning.TRAIT_GOAL_MAINTAIN):
        return Goal.MAINTAIN
    return Goal.NONE

