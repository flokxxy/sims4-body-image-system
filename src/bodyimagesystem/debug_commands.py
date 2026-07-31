"""Temporary in-game console commands for vertical-slice playtesting.

Remove the call to ``install`` from startup (and then this module) when proper
mirror interactions and a player-facing diagnostics flow replace the commands.
"""

from bodyimagesystem import sims_api, tuning
from bodyimagesystem.domain import Goal
from bodyimagesystem.tracking import SNAPSHOT_UNSET, sample_sim


_INSTALLED = False
_REGISTERED_COMMANDS = []

GOAL_ALIASES = {
    "lose": Goal.LOSE_WEIGHT,
    "lose_weight": Goal.LOSE_WEIGHT,
    "gain": Goal.GAIN_WEIGHT,
    "gain_weight": Goal.GAIN_WEIGHT,
    "muscle": Goal.GAIN_MUSCLE,
    "gain_muscle": Goal.GAIN_MUSCLE,
    "maintain": Goal.MAINTAIN,
    "none": Goal.NONE,
    "clear": Goal.NONE,
}

STATISTICS = (
    ("self_esteem", tuning.STATISTIC_SELF_ESTEEM),
    ("fat", tuning.COMMODITY_FAT),
    ("fat_snapshot", tuning.STATISTIC_FAT_SNAPSHOT),
    ("fit", tuning.COMMODITY_FIT),
    ("fit_snapshot", tuning.STATISTIC_FIT_SNAPSHOT),
    ("stagnation_days", tuning.STATISTIC_STAGNATION_DAYS),
    ("goal_achieved_flag", tuning.STATISTIC_GOAL_ACHIEVED_FLAG),
)


def parse_goal(value):
    if value is None:
        return None
    normalized = value.strip().lower().replace("-", "_")
    return GOAL_ALIASES.get(normalized)


def _active_sim_info(connection):
    import services

    manager = services.client_manager()
    if manager is None:
        return None
    client = manager.get(connection)
    if client is None:
        return None

    active_sim = getattr(client, "active_sim", None)
    if callable(active_sim):
        active_sim = active_sim()
    if active_sim is None:
        active_sim_info = getattr(client, "active_sim_info", None)
        if callable(active_sim_info):
            active_sim_info = active_sim_info()
        return active_sim_info
    return getattr(active_sim, "sim_info", active_sim)


def collect_status(sim_info):
    values = {
        name: sims_api.get_statistic_value(sim_info, statistic_id)
        for name, statistic_id in STATISTICS
    }
    values["goal"] = sims_api.current_goal(sim_info).value
    values["appearance_focused"] = sims_api.has_trait(
        sim_info,
        tuning.TRAIT_APPEARANCE_FOCUSED,
    )
    values["fat_delta"] = _pending_delta(
        values["fat"],
        values["fat_snapshot"],
    )
    values["fit_delta"] = _pending_delta(
        values["fit"],
        values["fit_snapshot"],
    )
    return values


def _pending_delta(current, snapshot):
    if current is None or snapshot is None or snapshot == SNAPSHOT_UNSET:
        return None
    return current - snapshot


def _format_value(value):
    if value is None:
        return "unavailable"
    if isinstance(value, float):
        return "{0:.2f}".format(value)
    return str(value)


def _write_status(output, sim_info, values=None):
    if values is None:
        values = collect_status(sim_info)

    sim_id = getattr(sim_info, "sim_id", "unknown")
    output("BIS status for active Sim (sim_id={0})".format(sim_id))
    output(
        "goal={0}; appearance_focused={1}".format(
            values["goal"],
            values["appearance_focused"],
        )
    )
    output("self_esteem={0}".format(_format_value(values["self_esteem"])))
    output(
        "fat={0}; snapshot={1}; pending_delta={2}".format(
            _format_value(values["fat"]),
            _format_value(values["fat_snapshot"]),
            _format_value(values["fat_delta"]),
        )
    )
    output(
        "fit={0}; snapshot={1}; pending_delta={2}".format(
            _format_value(values["fit"]),
            _format_value(values["fit_snapshot"]),
            _format_value(values["fit_delta"]),
        )
    )
    output(
        "stagnation_days={0}; goal_achieved_flag={1}".format(
            _format_value(values["stagnation_days"]),
            _format_value(values["goal_achieved_flag"]),
        )
    )


def _reset_goal_progress(sim_info):
    failed = []
    for name, statistic_id in (
        ("stagnation_days", tuning.STATISTIC_STAGNATION_DAYS),
        ("goal_achieved_flag", tuning.STATISTIC_GOAL_ACHIEVED_FLAG),
    ):
        if not sims_api.set_statistic_value(sim_info, statistic_id, 0):
            failed.append(name)
    return failed


def install():
    """Register temporary console commands once per Python session."""
    global _INSTALLED
    if _INSTALLED:
        return

    import sims4.commands

    @sims4.commands.Command(
        "bis.goal",
        command_type=sims4.commands.CommandType.Live,
    )
    def _command_goal(goal_name: str = "", _connection=None):
        output = sims4.commands.CheatOutput(_connection)
        sim_info = _active_sim_info(_connection)
        if sim_info is None:
            output("BIS: no active Sim was found.")
            return False

        goal = parse_goal(goal_name)
        if goal is None:
            output(
                "Usage: bis.goal lose_weight|gain_weight|gain_muscle|"
                "maintain|none"
            )
            output("Current goal: {0}".format(sims_api.current_goal(sim_info).value))
            return False

        if not sims_api.set_goal(sim_info, goal):
            output("BIS: goal traits are unavailable; check tuning IDs/package.")
            return False

        failed_resets = _reset_goal_progress(sim_info)
        output("BIS goal set to: {0}".format(goal.value))
        if failed_resets:
            output(
                "Warning: could not reset {0}.".format(
                    ", ".join(failed_resets)
                )
            )
        return True

    @sims4.commands.Command(
        "bis.sample",
        command_type=sims4.commands.CommandType.Live,
    )
    def _command_sample(_connection=None):
        output = sims4.commands.CheatOutput(_connection)
        sim_info = _active_sim_info(_connection)
        if sim_info is None:
            output("BIS: no active Sim was found.")
            return False

        before = collect_status(sim_info)
        output(
            "BIS sampling: pending fat_delta={0}; fit_delta={1}".format(
                _format_value(before["fat_delta"]),
                _format_value(before["fit_delta"]),
            )
        )
        sample_sim(sim_info)
        output("BIS sampling invoked; snapshots/status after the run:")
        _write_status(output, sim_info)
        return True

    @sims4.commands.Command(
        "bis.status",
        command_type=sims4.commands.CommandType.Live,
    )
    def _command_status(_connection=None):
        output = sims4.commands.CheatOutput(_connection)
        sim_info = _active_sim_info(_connection)
        if sim_info is None:
            output("BIS: no active Sim was found.")
            return False
        _write_status(output, sim_info)
        return True

    _REGISTERED_COMMANDS.extend(
        (_command_goal, _command_sample, _command_status)
    )
    _INSTALLED = True
