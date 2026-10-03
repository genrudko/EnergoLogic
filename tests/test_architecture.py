from __future__ import annotations

import ast
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "src" / "energologic" / "core"


class ArchitectureTests(unittest.TestCase):
    def test_runtime_has_no_third_party_dependencies(self):
        data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(data["project"]["dependencies"], [])

    def test_core_does_not_import_frontends_or_forbidden_stacks(self):
        forbidden_roots = {
            "win32com",
            "pythoncom",
            "openai",
            "langchain",
            "pandapower",
        }

        for path in sorted(CORE.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    roots = {alias.name.split(".", 1)[0] for alias in node.names}
                    self.assertTrue(
                        roots.isdisjoint(forbidden_roots),
                        f"{path} imports forbidden stack: {roots & forbidden_roots}",
                    )
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    root = module.split(".", 1)[0]
                    self.assertNotIn(
                        root,
                        forbidden_roots,
                        f"{path} imports forbidden stack: {module}",
                    )
                    self.assertFalse(
                        module.startswith("energologic.frontends"),
                        f"{path} depends on frontend: {module}",
                    )


if __name__ == "__main__":
    unittest.main()
