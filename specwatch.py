
import ast
import re
from pathlib import Path


def find_functions(source):
    """Extract top-level function signatures from Python source."""
    tree = ast.parse(source)
    functions = {}

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            positional = node.args.posonlyargs + node.args.args
            required_count = len(positional) - len(node.args.defaults)

            required_names = [
                arg.arg for arg in positional[:required_count]
            ]

            required_keyword_only = [
                arg.arg
                for arg, default in zip(
                    node.args.kwonlyargs,
                    node.args.kw_defaults,
                )
                if default is None
            ]

            functions[node.name] = {
                "required_count": required_count,
                "required_names": required_names,
                "required_keyword_only": required_keyword_only,
                "positional_only_count": len(node.args.posonlyargs),
                "positional_names": [arg.arg for arg in positional],
                "has_varargs": node.args.vararg is not None,
                "has_kwargs": node.args.kwarg is not None,
            }

    return functions


def check_call(node, signature):
    """Return missing required parameter names for a simple function call."""
    positional_names = signature["positional_names"]
    positional_only_count = signature["positional_only_count"]

    # Positional arguments fill parameters from left to right.
    supplied_names = set(positional_names[:len(node.args)])

    # Keyword arguments can fill parameters unless they are positional-only.
    for keyword in node.keywords:
        if keyword.arg is not None:
            if keyword.arg not in positional_names[:positional_only_count]:
                supplied_names.add(keyword.arg)

    required_names = (
        signature["required_names"]
        + signature["required_keyword_only"]
    )

    missing = [
        name for name in required_names
        if name not in supplied_names
    ]

    return missing


def scan_documentation(source, readme):
    """Find README calls that omit required arguments."""
    functions = find_functions(source)
    issues = []

    code_blocks = re.findall(
        r"```python\s*(.*?)```",
        readme,
        flags=re.DOTALL | re.IGNORECASE,
    )

    for block_number, block in enumerate(code_blocks, start=1):
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

            signature = functions[name]
            missing = check_call(node, signature)

            if missing:
                issues.append(
                    f"{name}() may be missing required argument(s): "
                    f"{', '.join(missing)}."
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
