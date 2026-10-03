from __future__ import annotations

import unittest

from energologic.core import decode_model, validate_model


class ValidationTests(unittest.TestCase):
    def test_duplicate_ids_and_broken_references_are_reported(self):
        model = decode_model(
            {
                "schema_version": "0.1",
                "model_id": "invalid",
                "elements": [
                    {
                        "id": "e1",
                        "kind": "device",
                        "terminals": [{"id": "t1"}, {"id": "t1"}],
                    },
                    {"id": "e1", "kind": "device"},
                    {"id": "e2", "kind": "device", "terminals": [{"id": "t2"}]},
                ],
                "connections": [
                    {
                        "id": "c1",
                        "endpoints": [
                            {"element_id": "missing", "terminal_id": "x"},
                            {"element_id": "e2", "terminal_id": "missing"},
                        ],
                    },
                    {
                        "id": "c1",
                        "endpoints": [
                            {"element_id": "e2", "terminal_id": "t2"},
                            {"element_id": "e2", "terminal_id": "t2"},
                        ],
                    },
                ],
            }
        )

        codes = [issue.code for issue in validate_model(model)]
        self.assertEqual(
            codes,
            sorted(
                [
                    "duplicate_connection_id",
                    "duplicate_element_id",
                    "duplicate_terminal_id",
                    "unknown_element",
                    "unknown_terminal",
                    "degenerate_connection",
                ]
            ),
        )

    def test_valid_model_has_no_issues(self):
        model = decode_model(
            {
                "schema_version": "0.1",
                "model_id": "valid",
                "elements": [
                    {"id": "a", "kind": "bus", "terminals": [{"id": "t"}]},
                    {"id": "b", "kind": "device", "terminals": [{"id": "x"}]},
                ],
                "connections": [
                    {
                        "id": "c",
                        "endpoints": [
                            {"element_id": "a", "terminal_id": "t"},
                            {"element_id": "b", "terminal_id": "x"},
                        ],
                    }
                ],
            }
        )
        self.assertEqual(validate_model(model), ())


if __name__ == "__main__":
    unittest.main()
