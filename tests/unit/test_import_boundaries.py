import ast
from pathlib import Path


def test_reusable_layers_do_not_import_concrete_providers() -> None:
    project_root = Path(__file__).parents[2]
    reusable_roots = (
        project_root / "src/options_analysis/domain",
        project_root / "src/options_analysis/services",
        project_root / "src/options_analysis/analytics",
    )
    forbidden = ("options_analysis.providers.fake", "options_analysis.providers.schwab")
    violations: list[str] = []

    for root in reusable_roots:
        for source_file in root.glob("*.py"):
            tree = ast.parse(source_file.read_text(), filename=str(source_file))
            imports = [
                node.module
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom) and node.module is not None
            ]
            imports.extend(
                alias.name
                for node in ast.walk(tree)
                if isinstance(node, ast.Import)
                for alias in node.names
            )
            if any(name.startswith(forbidden) for name in imports):
                violations.append(str(source_file.relative_to(project_root)))

    assert violations == []
