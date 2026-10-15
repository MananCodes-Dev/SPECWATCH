
import argparse
import ast
import re
from pathlib import Path


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
    """Return missing required parameter names for a simple call."""
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
    """Find README calls that may omit required arguments."""
    functions = find_functions(source)
    issues = []

    blocks = re.findall(
        r"```python\s*(.*?)```",
        readme,
        flags=re.DOTALL | re.IGNORECASE,
    )

    for block_number, block in enumerate(blocks, start=1):
        try:
            tree = ast.parse(block)
        except SyntaxError:
            issues.append(
                f"README Python block {block_number} contains invalid syntax."
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
                issues.append(
                    f"{name}() may be missing required argument(s): "
                    f"{', '.join(missing)}."
                )

    return issues


def scan_project(project_path):
    """Scan README examples against functions in a project."""
    project_path = Path(project_path).resolve()
    readme_path = project_path / "README.md"

    if not project_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {project_path}")

    if not readme_path.is_file():
        raise FileNotFoundError(f"README.md not found in {project_path}")

    readme = readme_path.read_text(encoding="utf-8")
    all_functions = {}
    issues = []

    for python_file in project_path.rglob("*.py"):
        if ".venv" in python_file.parts or ".git" in python_file.parts:
            continue
        if "__pycache__" in python_file.parts:
            continue

        try:
            source = python_file.read_text(encoding="utf-8")
            functions = find_functions(source)
            all_functions.update(functions)
        except (OSError, SyntaxError) as error:
            issues.append(f"Could not analyze {python_file.name}: {error}")

    # Parse the README once, then check calls against discovered functions.
    blocks = re.findall(
        r"```python\s*(.*?)```",
        readme,
        flags=re.DOTALL | re.IGNORECASE,
    )

    for block_number, block in enumerate(blocks, start=1):
        try:
            tree = ast.parse(block)
        except SyntaxError:
            issues.append(
                f"README Python block {block_number} contains invalid syntax."
            )
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Name):
                continue

            name = node.func.id
            if name not in all_functions:
                continue

            missing = check_call(node, all_functions[name])
            if missing:
                issues.append(
                    f"{name}() may be missing required argument(s): "
                    f"{', '.join(missing)}."
                )

    return issues


def main():
    parser = argparse.ArgumentParser(
        description="Detect possible code/documentation mismatches."
    )
    parser.add_argument(
        "--project",
        default=".",
        help="Path to a Python project (default: current directory).",
    )
    args = parser.parse_args()

    try:
        issues = scan_project(args.project)
    except (OSError, NotADirectoryError) as error:
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
