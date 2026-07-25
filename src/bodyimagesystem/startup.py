"""Install game hooks and daily alarms.

The exact zone hook is intentionally isolated here because Sims 4 patch changes
often affect lifecycle names. Verify this module against decompiled scripts
before the first in-game test.
"""

from bodyimagesystem.logger import log, log_exception

_INSTALLED = False
_ALARMS = {}


def install():
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True
    log("startup installed")

    try:
        _install_zone_spin_up_hook()
    except Exception as exc:
        log_exception("Could not install zone spin-up hook", exc)


def _install_zone_spin_up_hook():
    import zone

    from bodyimagesystem.injector import inject_to

    # This hook name is common in TS4 script mods, but still must be checked
    # against the current decompiled game scripts before packaging.
    @inject_to(zone.Zone, "on_loading_screen_animation_finished")
    def _bis_zone_loaded(original, self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        setup_zone_alarms()
        return result


def setup_zone_alarms():
    try:
        import services

        sim_info_manager = services.sim_info_manager()
        if sim_info_manager is None:
            return

        for sim in sim_info_manager.instanced_sims_gen():
            sim_info = getattr(sim, "sim_info", sim)
            setup_sim_alarm(sim_info)
    except Exception as exc:
        log_exception("Failed to set up zone alarms", exc)


def setup_sim_alarm(sim_info):
    if sim_info.sim_id in _ALARMS:
        return

    try:
        import alarms
        import date_and_time

        from bodyimagesystem.tracking import sample_sim

        def _run_alarm(_alarm_handle):
            sample_sim(sim_info)

        handle = alarms.add_alarm(
            sim_info,
            date_and_time.create_time_span(hours=24),
            _run_alarm,
            repeating=True,
        )
        _ALARMS[sim_info.sim_id] = handle
        log("daily alarm added for sim_id={0}".format(sim_info.sim_id))
    except Exception as exc:
        log_exception("Failed to create sim alarm", exc)
