from __future__ import annotations

import ast
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "src" / "energologic" / "core"
DOMAIN = ROOT / "src" / "energologic" / "domain"


FORBIDDEN_ROOTS = {
    "win32com",
    "pythoncom",
    "openai",
    "langchain",
    "pandapower",
}


def _imports(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            yield node.module or ""


class ArchitectureTests(unittest.TestCase):
    def test_runtime_has_no_third_party_dependencies(self):
        data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(data["project"]["dependencies"], [])

    def test_core_does_not_import_higher_layers_or_forbidden_stacks(self):
        for path in sorted(CORE.rglob("*.py")):
            for module in _imports(path):
                root = module.split(".", 1)[0]
                self.assertNotIn(
                    root,
                    FORBIDDEN_ROOTS,
                    f"{path} imports forbidden stack: {module}",
                )
                self.assertFalse(
                    module.startswith("energologic.frontends"),
                    f"{path} depends on frontend: {module}",
                )
                self.assertFalse(
                    module.startswith("energologic.domain"),
                    f"{path} depends on domain profile: {module}",
                )

    def test_domain_depends_only_downward_not_on_frontends_or_forbidden_stacks(self):
        for path in sorted(DOMAIN.rglob("*.py")):
            for module in _imports(path):
                root = module.split(".", 1)[0]
                self.assertNotIn(
                    root,
                    FORBIDDEN_ROOTS,
                    f"{path} imports forbidden stack: {module}",
                )
                self.assertFalse(
                    module.startswith("energologic.frontends"),
                    f"{path} depends on frontend: {module}",
                )


if __name__ == "__main__":
    unittest.main()
