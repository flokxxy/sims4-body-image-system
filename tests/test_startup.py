import sys
import types
import unittest
from unittest import mock

from bodyimagesystem import startup, tracking


class StartupAlarmTests(unittest.TestCase):
    def setUp(self):
        startup._ALARMS.clear()
        self.sim_info = types.SimpleNamespace(sim_id=123, is_selectable=True)
        self.alarms = types.SimpleNamespace(add_alarm=mock.Mock(return_value="handle"))
        self.date_and_time = types.SimpleNamespace(
            create_time_span=mock.Mock(return_value="24-hours")
        )
        self.module_patch = mock.patch.dict(
            sys.modules,
            {
                "alarms": self.alarms,
                "date_and_time": self.date_and_time,
            },
        )
        self.module_patch.start()

    def tearDown(self):
        self.module_patch.stop()
        startup._ALARMS.clear()

    def test_selectable_sim_gets_baseline_before_daily_alarm(self):
        with mock.patch.object(
            tracking,
            "ensure_initial_state",
            return_value=tracking.InitializationState(True, True),
        ) as ensure_initial_state:
            startup.setup_sim_alarm(self.sim_info)

        ensure_initial_state.assert_called_once_with(self.sim_info)
        self.date_and_time.create_time_span.assert_called_once_with(hours=24)
        self.alarms.add_alarm.assert_called_once()
        self.assertEqual(startup._ALARMS[123], "handle")

    def test_non_selectable_sim_does_not_get_alarm(self):
        self.sim_info.is_selectable = False

        with mock.patch.object(
            tracking,
            "ensure_initial_state",
        ) as ensure_initial_state:
            startup.setup_sim_alarm(self.sim_info)

        ensure_initial_state.assert_not_called()
        self.alarms.add_alarm.assert_not_called()
        self.assertNotIn(123, startup._ALARMS)

    def test_existing_alarm_is_not_duplicated(self):
        startup._ALARMS[123] = "existing"

        startup.setup_sim_alarm(self.sim_info)

        self.alarms.add_alarm.assert_not_called()
        self.assertEqual(startup._ALARMS[123], "existing")


if __name__ == "__main__":
    unittest.main()
