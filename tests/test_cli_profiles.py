from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CliProfileTests(unittest.TestCase):
    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "energologic", *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_default_validate_remains_structural_and_backwards_compatible(self):
        result = self._run("validate", "examples/minimal.energologic.json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            {
                "valid": True,
                "schema_version": "0.1",
                "model_id": "example:minimal",
            },
        )

    def test_electrical_profile_rejects_structural_only_fixture(self):
        result = self._run(
            "validate",
            "examples/minimal.energologic.json",
            "--profile",
            "electrical-v1",
        )
        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stderr)
        self.assertFalse(payload["valid"])
        codes = {issue["code"] for issue in payload["issues"]}
        self.assertIn("unsupported_element_kind", codes)
        self.assertIn("missing_nominal_voltage", codes)

    def test_electrical_profile_accepts_kru35_slice(self):
        result = self._run(
            "validate",
            "examples/kru35-v1-cell.electrical-v1.json",
            "--profile",
            "electrical-v1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            {
                "valid": True,
                "schema_version": "0.1",
                "model_id": "kru35:v1-cell",
                "profile": "electrical-v1",
            },
        )


if __name__ == "__main__":
    unittest.main()
