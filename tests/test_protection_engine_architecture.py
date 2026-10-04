from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "src" / "energologic" / "protection" / "runtime.py"


def imports(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            yield node.module or ""


class ProtectionEngineArchitectureTests(unittest.TestCase):
    def test_runtime_has_no_wall_clock_or_async_dependency(self):
        forbidden = {"time", "datetime", "asyncio"}
        for module in imports(RUNTIME):
            self.assertNotIn(
                module.split(".", 1)[0],
                forbidden,
                f"runtime depends on wall-clock/async module: {module}",
            )

    def test_runtime_has_no_cross_workstream_execution_dependency(self):
        forbidden_prefixes = (
            "energologic.operational",
            "energologic.solver",
            "energologic.frontends",
            "energologic.terminology",
        )
        for module in imports(RUNTIME):
            for prefix in forbidden_prefixes:
                self.assertFalse(
                    module.startswith(prefix),
                    f"runtime depends on {prefix}: {module}",
                )


if __name__ == "__main__":
    unittest.main()
