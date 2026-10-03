from __future__ import annotations

import unittest

from energologic.core import ModelDecodeError, decode_model


class DecodeContractTests(unittest.TestCase):
    def test_unknown_top_level_field_is_rejected(self):
        with self.assertRaises(ModelDecodeError):
            decode_model(
                {
                    "schema_version": "0.1",
                    "model_id": "x",
                    "unexpected": True,
                }
            )

    def test_unknown_schema_version_is_rejected(self):
        with self.assertRaises(ModelDecodeError):
            decode_model({"schema_version": "9.9", "model_id": "x"})

    def test_connection_requires_exactly_two_endpoints(self):
        with self.assertRaises(ModelDecodeError):
            decode_model(
                {
                    "schema_version": "0.1",
                    "model_id": "x",
                    "connections": [{"id": "c", "endpoints": []}],
                }
            )


if __name__ == "__main__":
    unittest.main()
