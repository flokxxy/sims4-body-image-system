"""BodyImageSystem script package.

The Sims 4 loads script mods by importing Python modules from the ts4script zip.
Keep import side effects small: startup installs the game hooks, while pure
domain logic remains testable outside the game.
"""

MOD_NAMESPACE = "BodyImageSystem"
MOD_VERSION = "0.1.0"

def _running_inside_sims():
    try:
        import importlib.util

        return importlib.util.find_spec("sims4") is not None
    except Exception:
        return False


if _running_inside_sims():
    try:
        from bodyimagesystem import startup as _startup

        _startup.install()
    except Exception as exc:  # pragma: no cover - only exercised inside the game.
        try:
            from bodyimagesystem.logger import log_exception

            log_exception("Failed to install BodyImageSystem startup hooks", exc)
        except Exception:
            pass
