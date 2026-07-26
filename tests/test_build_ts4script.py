import os
import subprocess
import sys
import unittest
import zipfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_SCRIPT = os.path.join(ROOT, "tools", "build_ts4script.py")
ARTIFACT = os.path.join(ROOT, "dist", "BodyImageSystem.ts4script")


class BuildTs4ScriptTests(unittest.TestCase):
    def test_smoke_build_contains_one_flat_pyc_per_source_module(self):
        subprocess.run(
            [sys.executable, BUILD_SCRIPT, "--skip-version-check"],
            check=True,
            capture_output=True,
            text=True,
        )

        source_modules = {
            filename[:-3] + ".pyc"
            for filename in os.listdir(os.path.join(ROOT, "src", "bodyimagesystem"))
            if filename.endswith(".py")
        }

        with zipfile.ZipFile(ARTIFACT) as archive:
            names = archive.namelist()

        self.assertEqual(
            set(names),
            {"bodyimagesystem/" + filename for filename in source_modules},
        )
        self.assertEqual(len(names), len(set(names)))
        self.assertFalse(any("__pycache__" in name for name in names))


if __name__ == "__main__":
    unittest.main()
