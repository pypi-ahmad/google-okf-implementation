from __future__ import annotations

import ast
from pathlib import Path

PUBLIC_API_ROOTS = [
    Path("src/enterprise_okf_ai"),
    Path("src/agent"),
    Path("src/rag"),
    Path("src/ingest"),
    Path("src/graph"),
    Path("src/validators"),
    Path("src/vector_db"),
]


def test_prompt8_public_functions_are_typed_and_documented() -> None:
    violations: list[str] = []

    for root in PUBLIC_API_ROOTS:
        for module_path in root.rglob("*.py"):
            tree = ast.parse(module_path.read_text(encoding="utf-8"))

            for node in tree.body:
                if isinstance(node, ast.FunctionDef):
                    if node.name.startswith("_"):
                        continue
                    if node.returns is None:
                        violations.append(f"{module_path}:{node.name} missing return annotation")
                    if not ast.get_docstring(node):
                        violations.append(f"{module_path}:{node.name} missing docstring")

                if isinstance(node, ast.ClassDef):
                    for method in node.body:
                        if not isinstance(method, ast.FunctionDef):
                            continue
                        if method.name.startswith("_"):
                            continue
                        if method.name.startswith("__") and method.name.endswith("__"):
                            continue
                        if method.returns is None:
                            violations.append(
                                f"{module_path}:{node.name}.{method.name} missing return annotation"
                            )
                        if not ast.get_docstring(method):
                            violations.append(
                                f"{module_path}:{node.name}.{method.name} missing docstring"
                            )

    assert violations == []
