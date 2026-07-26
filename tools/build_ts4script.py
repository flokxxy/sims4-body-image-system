#!/usr/bin/env python3
"""Build BodyImageSystem.ts4script from src/.

Production builds should run with Python 3.7 because The Sims 4 embeds Python
3.7 bytecode. For local iteration you can use --skip-version-check, but do not
ship that artifact.
"""

import argparse
import compileall
import os
import shutil
import sys
import zipfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
BUILD = os.path.join(ROOT, "build", "ts4script")
OUT = os.path.join(ROOT, "dist", "BodyImageSystem.ts4script")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-version-check", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.skip_version_check and sys.version_info[:2] != (3, 7):
        raise SystemExit(
            "Use Python 3.7 to build .ts4script, or pass --skip-version-check "
            "only for local smoke tests."
        )

    if os.path.exists(BUILD):
        shutil.rmtree(BUILD)
    os.makedirs(os.path.dirname(BUILD), exist_ok=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)

    shutil.copytree(
        SRC,
        BUILD,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    ok = compileall.compile_dir(BUILD, quiet=1, force=True, legacy=True)
    if not ok:
        raise SystemExit("Bytecode compilation failed")

    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as archive:
        for dirpath, _, filenames in os.walk(BUILD):
            for filename in filenames:
                if not filename.endswith(".pyc"):
                    continue
                path = os.path.join(dirpath, filename)
                relpath = os.path.relpath(path, BUILD)
                archive.write(path, relpath)

    print(OUT)


if __name__ == "__main__":
    main()
