from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "src" / "energologic" / "protection" / "breaker_failure.py"


def imports(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            yield node.module or ""


class BreakerFailureArchitectureTests(unittest.TestCase):
    def test_no_wall_clock_or_async_dependency(self):
        for module in imports(MODULE):
            self.assertNotIn(
                module.split(".", 1)[0],
                {"time", "datetime", "asyncio"},
                f"breaker failure uses wall clock/async: {module}",
            )

    def test_no_cross_workstream_runtime_dependency(self):
        for module in imports(MODULE):
            for prefix in (
                "energologic.operational",
                "energologic.solver",
                "energologic.frontends",
                "energologic.terminology",
            ):
                self.assertFalse(
                    module.startswith(prefix),
                    f"breaker failure depends on {prefix}: {module}",
                )


if __name__ == "__main__":
    unittest.main()
