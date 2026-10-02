from __future__ import annotations

import unittest

from energologic.core import canonical_json, decode_model, fingerprint, model_to_data


class CanonicalCodecTests(unittest.TestCase):
    def _model_data(self):
        return {
            "schema_version": "0.1",
            "model_id": "test:model",
            "elements": [
                {
                    "id": "z",
                    "kind": "device",
                    "terminals": [{"id": "b"}, {"id": "a"}],
                    "attributes": {"nested": {"y": 2, "x": 1}},
                },
                {
                    "id": "a",
                    "kind": "bus",
                    "terminals": [{"id": "t"}],
                },
            ],
            "connections": [
                {
                    "id": "c",
                    "endpoints": [
                        {"element_id": "z", "terminal_id": "a"},
                        {"element_id": "a", "terminal_id": "t"},
                    ],
                }
            ],
            "metadata": {"b": 2, "a": 1},
        }

    def test_semantically_equivalent_identity_order_has_same_canonical_form(self):
        first = self._model_data()
        second = self._model_data()
        second["elements"] = list(reversed(second["elements"]))
        second["elements"][0]["terminals"] = list(
            reversed(second["elements"][0]["terminals"])
        )
        second["connections"][0]["endpoints"] = list(
            reversed(second["connections"][0]["endpoints"])
        )

        model_a = decode_model(first)
        model_b = decode_model(second)

        self.assertEqual(canonical_json(model_a), canonical_json(model_b))
        self.assertEqual(fingerprint(model_a), fingerprint(model_b))

    def test_canonical_json_has_exact_single_lf(self):
        payload = canonical_json(decode_model(self._model_data()))
        self.assertTrue(payload.endswith("\n"))
        self.assertFalse(payload.endswith("\n\n"))
        self.assertNotIn("\r", payload)

    def test_round_trip_preserves_canonical_data(self):
        model = decode_model(self._model_data())
        round_trip = decode_model(model_to_data(model))
        self.assertEqual(canonical_json(model), canonical_json(round_trip))


if __name__ == "__main__":
    unittest.main()
