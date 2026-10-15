
import ast
import re
from pathlib import Path


def find_required_arguments(source):
    """Return the number of required positional arguments per function."""
    tree = ast.parse(source)
    functions = {}

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        positional = node.args.posonlyargs + node.args.args
        defaults = node.args.defaults

        required_count = len(positional) - len(defaults)
        functions[node.name] = required_count

    return functions


def scan_documentation(source, readme):
    """Find README calls that supply too few positional arguments."""
    functions = find_required_arguments(source)
    issues = []

    code_blocks = re.findall(
        r"```python\s*(.*?)```",
        readme,
        flags=re.DOTALL,
    )

    for block in code_blocks:
        try:
            tree = ast.parse(block)
        except SyntaxError:
            issues.append("Could not parse a Python example in README.md.")
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            if not isinstance(node.func, ast.Name):
                continue

            name = node.func.id

            if name not in functions:
                continue

            required = functions[name]
            supplied = len(node.args)

            # Keyword arguments can satisfy required parameters.
            supplied_names = {
                keyword.arg
                for keyword in node.keywords
                if keyword.arg is not None
            }

            # Find the function definition to identify parameter names.
            source_tree = ast.parse(source)
            definition = next(
                (
                    item
                    for item in ast.walk(source_tree)
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and item.name == name
                ),
                None,
            )

            if definition is None:
                continue

            positional = (
                definition.args.posonlyargs + definition.args.args
            )
            required_names = [
                arg.arg
                for arg in positional[:required]
            ]

            satisfied = sum(
                1 for arg in required_names
                if arg in supplied_names
            )

            missing = max(0, required - supplied - satisfied)

            if missing > 0:
                issues.append(
                    f"{name}() may be missing {missing} required "
                    f"argument(s): requires {required}, "
                    f"example supplies {supplied} positional argument(s)."
                )

    return issues


def main():
    source_path = Path("calculator.py")
    readme_path = Path("README.md")

    if not source_path.exists() or not readme_path.exists():
        print("ERROR: calculator.py and README.md must exist.")
        return

    source = source_path.read_text(encoding="utf-8")
    readme = readme_path.read_text(encoding="utf-8")

    try:
        issues = scan_documentation(source, readme)
    except SyntaxError as error:
        print(f"ERROR: Could not parse Python source: {error}")
        return

    if issues:
        for issue in issues:
            print(f"WARNING: {issue}")
    else:
        print("No missing-argument issues detected.")

    print("Scan complete.")


if __name__ == "__main__":
    main()
