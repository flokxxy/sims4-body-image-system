import unittest
import sys
import types
from unittest import mock

from bodyimagesystem import debug_commands, tuning
from bodyimagesystem.domain import Goal


class GoalParsingTests(unittest.TestCase):
    def test_documented_goal_names_are_parsed(self):
        self.assertEqual(debug_commands.parse_goal("lose_weight"), Goal.LOSE_WEIGHT)
        self.assertEqual(debug_commands.parse_goal("gain-weight"), Goal.GAIN_WEIGHT)
        self.assertEqual(debug_commands.parse_goal("muscle"), Goal.GAIN_MUSCLE)
        self.assertEqual(debug_commands.parse_goal("maintain"), Goal.MAINTAIN)
        self.assertEqual(debug_commands.parse_goal("none"), Goal.NONE)

    def test_unknown_or_empty_goal_is_rejected(self):
        self.assertIsNone(debug_commands.parse_goal(""))
        self.assertIsNone(debug_commands.parse_goal("unknown"))
        self.assertIsNone(debug_commands.parse_goal(None))


class StatusTests(unittest.TestCase):
    def test_collect_status_reports_pending_body_deltas(self):
        values = {
            tuning.STATISTIC_SELF_ESTEEM: 55,
            tuning.COMMODITY_FAT: 20,
            tuning.STATISTIC_FAT_SNAPSHOT: 14,
            tuning.COMMODITY_FIT: 40,
            tuning.STATISTIC_FIT_SNAPSHOT: 43,
            tuning.STATISTIC_STAGNATION_DAYS: 2,
            tuning.STATISTIC_GOAL_ACHIEVED_FLAG: 0,
        }

        with mock.patch.object(
            debug_commands.sims_api,
            "get_statistic_value",
            side_effect=lambda _sim, statistic_id: values[statistic_id],
        ), mock.patch.object(
            debug_commands.sims_api,
            "current_goal",
            return_value=Goal.GAIN_WEIGHT,
        ), mock.patch.object(
            debug_commands.sims_api,
            "has_trait",
            return_value=True,
        ):
            status = debug_commands.collect_status(object())

        self.assertEqual(status["goal"], "gain_weight")
        self.assertTrue(status["appearance_focused"])
        self.assertEqual(status["fat_delta"], 6)
        self.assertEqual(status["fit_delta"], -3)

    def test_uninitialized_snapshot_has_no_pending_delta(self):
        self.assertIsNone(debug_commands._pending_delta(20, -999))


class CommandInstallationTests(unittest.TestCase):
    def setUp(self):
        debug_commands._INSTALLED = False
        debug_commands._REGISTERED_COMMANDS[:] = []

    def tearDown(self):
        debug_commands._INSTALLED = False
        debug_commands._REGISTERED_COMMANDS[:] = []

    def test_all_three_commands_are_registered_once(self):
        registered_names = []
        commands = types.ModuleType("sims4.commands")
        commands.CommandType = types.SimpleNamespace(Live="live")
        commands.CheatOutput = mock.Mock()

        def command(name, command_type=None):
            self.assertEqual(command_type, "live")
            registered_names.append(name)
            return lambda function: function

        commands.Command = command
        sims4 = types.ModuleType("sims4")
        sims4.commands = commands

        with mock.patch.dict(
            sys.modules,
            {"sims4": sims4, "sims4.commands": commands},
        ):
            debug_commands.install()
            debug_commands.install()

        self.assertEqual(
            registered_names,
            ["bis.goal", "bis.sample", "bis.status"],
        )
        self.assertEqual(len(debug_commands._REGISTERED_COMMANDS), 3)


if __name__ == "__main__":
    unittest.main()
