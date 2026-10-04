from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTECTION = ROOT / "src" / "energologic" / "protection"
CORE = ROOT / "src" / "energologic" / "core"
DOMAIN = ROOT / "src" / "energologic" / "domain"

FORBIDDEN_ROOTS = {
    "win32com",
    "pythoncom",
    "openai",
    "langchain",
    "pandapower",
    "opendssdirect",
}


def imports(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            yield node.module or ""


class ProtectionSettingsArchitectureTests(unittest.TestCase):
    def test_protection_settings_package_is_headless_and_solver_neutral(self):
        for path in sorted(PROTECTION.rglob("*.py")):
            for module in imports(path):
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
                    module.startswith("energologic.solver"),
                    f"{path} depends on solver: {module}",
                )
                self.assertFalse(
                    module.startswith("energologic.operational"),
                    f"{path} depends on WS-6 operational runtime: {module}",
                )
                self.assertFalse(
                    module.startswith("energologic.terminology"),
                    f"{path} hard-depends on unmerged WS-2 runtime: {module}",
                )

    def test_core_and_domain_do_not_depend_upward_on_protection(self):
        for directory in (CORE, DOMAIN):
            for path in sorted(directory.rglob("*.py")):
                for module in imports(path):
                    self.assertFalse(
                        module.startswith("energologic.protection"),
                        f"{path} depends upward on protection layer: {module}",
                    )


if __name__ == "__main__":
    unittest.main()
