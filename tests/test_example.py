from __future__ import annotations

import unittest
from pathlib import Path

from energologic.core import load_model, validate_model


ROOT = Path(__file__).resolve().parents[1]


class ExampleTests(unittest.TestCase):
    def test_minimal_example_is_valid(self):
        model = load_model(ROOT / "examples" / "minimal.energologic.json")
        self.assertEqual(model.schema_version, "0.1")
        self.assertEqual(validate_model(model), ())


if __name__ == "__main__":
    unittest.main()
