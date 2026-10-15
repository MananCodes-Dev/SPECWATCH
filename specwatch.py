
import argparse
import ast
import re
from pathlib import Path


IGNORED_DIRECTORIES = {".venv", ".git", "__pycache__"}


def find_functions(source):
    """Extract function signatures from Python source."""
    tree = ast.parse(source)
    functions = {}

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        positional = node.args.posonlyargs + node.args.args
        required_count = len(positional) - len(node.args.defaults)

        functions[node.name] = {
            "required_names": [
                arg.arg for arg in positional[:required_count]
            ],
            "positional_only_count": len(node.args.posonlyargs),
            "positional_names": [arg.arg for arg in positional],
            "required_keyword_only": [
                arg.arg
                for arg, default in zip(
                    node.args.kwonlyargs,
                    node.args.kw_defaults,
                )
                if default is None
            ],
        }

    return functions


def check_call(node, signature):
    """Return missing required parameters for a simple function call."""
    positional_names = signature["positional_names"]
    positional_only_count = signature["positional_only_count"]

    supplied_names = set(positional_names[:len(node.args)])

    for keyword in node.keywords:
        if keyword.arg is not None:
            if keyword.arg not in positional_names[:positional_only_count]:
                supplied_names.add(keyword.arg)

    required_names = (
        signature["required_names"]
        + signature["required_keyword_only"]
    )

    return [
        name for name in required_names
        if name not in supplied_names
    ]


def scan_documentation(source, readme):
    """Find missing arguments in Python examples."""
    functions = find_functions(source)
    issues = []

    pattern = re.compile(
        r"```python\s*(.*?)```",
        flags=re.DOTALL | re.IGNORECASE,
    )

    for block_number, match in enumerate(pattern.finditer(readme), start=1):
        block = match.group(1)
        block_start_line = readme.count("\n", 0, match.start(1)) + 1

        try:
            tree = ast.parse(block)
        except SyntaxError as error:
            line = block_start_line + (error.lineno or 1) - 1
            issues.append(
                f"README.md:{line}: Python block {block_number} "
                "contains invalid syntax."
            )
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            if not isinstance(node.func, ast.Name):
                continue

            name = node.func.id

            if name not in functions:
                continue

            missing = check_call(node, functions[name])

            if missing:
                line = block_start_line + node.lineno - 1
                issues.append(
                    f"README.md:{line}: {name}() may be missing "
                    f"required argument(s): {', '.join(missing)}."
                )

    return issues


def scan_project(project_path):
    """Scan a project's README against its Python functions."""
    project_path = Path(project_path).resolve()
    readme_path = project_path / "README.md"

    if not project_path.is_dir():
        raise NotADirectoryError(
            f"Project directory not found: {project_path}"
        )

    if not readme_path.is_file():
        raise FileNotFoundError(
            f"README.md not found in {project_path}"
        )

    readme = readme_path.read_text(encoding="utf-8")
    all_functions = {}
    issues = []

    for python_file in project_path.rglob("*.py"):
        if any(part in IGNORED_DIRECTORIES for part in python_file.parts):
            continue

        try:
            source = python_file.read_text(encoding="utf-8")
            functions = find_functions(source)

            for name, signature in functions.items():
                if name in all_functions:
                    issues.append(
                        f"WARNING: Duplicate function name '{name}' "
                        "found in multiple files; results may be ambiguous."
                    )

                all_functions[name] = signature

        except (OSError, SyntaxError) as error:
            issues.append(
                f"Could not analyze {python_file}: {error}"
            )

    # Check the README against all discovered function signatures.
    for issue in scan_documentation_from_functions(readme, all_functions):
        issues.append(issue)

    return issues


def scan_documentation_from_functions(readme, functions):
    """Check README examples against discovered project functions."""
    issues = []

    pattern = re.compile(
        r"```python\s*(.*?)```",
        flags=re.DOTALL | re.IGNORECASE,
    )

    for block_number, match in enumerate(pattern.finditer(readme), start=1):
        block = match.group(1)
        block_start_line = readme.count("\n", 0, match.start(1)) + 1

        try:
            tree = ast.parse(block)
        except SyntaxError as error:
            line = block_start_line + (error.lineno or 1) - 1
            issues.append(
                f"README.md:{line}: Python block {block_number} "
                "contains invalid syntax."
            )
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            if not isinstance(node.func, ast.Name):
                continue

            name = node.func.id

            if name not in functions:
                continue

            missing = check_call(node, functions[name])

            if missing:
                line = block_start_line + node.lineno - 1
                issues.append(
                    f"README.md:{line}: {name}() may be missing "
                    f"required argument(s): {', '.join(missing)}."
                )

    return issues


def main():
    parser = argparse.ArgumentParser(
        description="Detect potential code/documentation mismatches."
    )

    parser.add_argument(
        "--project",
        default=".",
        help="Path to the project to scan (default: current directory).",
    )

    args = parser.parse_args()

    try:
        issues = scan_project(args.project)
    except (OSError, UnicodeError) as error:
        print(f"ERROR: {error}")
        return 1

    if issues:
        for issue in issues:
            print(f"WARNING: {issue}")
    else:
        print("No missing-argument issues detected.")

    print("Scan complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
