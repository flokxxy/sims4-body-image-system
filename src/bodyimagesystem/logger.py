"""Minimal file logger for early game bring-up."""

import os
import traceback


LOG_FILE_NAME = "BodyImageSystem.log"


def _log_path():
    # In game this resolves relative to the process working directory. If that
    # is not the Mods folder on a given patch, replace this with S4CL logging.
    return os.path.join(os.getcwd(), LOG_FILE_NAME)


def log(message):
    try:
        with open(_log_path(), "a") as handle:
            handle.write("[BodyImageSystem] {0}\n".format(message))
    except Exception:
        pass


def log_exception(message, exc):
    log("{0}: {1}".format(message, exc))
    try:
        with open(_log_path(), "a") as handle:
            handle.write(traceback.format_exc())
            handle.write("\n")
    except Exception:
        pass

