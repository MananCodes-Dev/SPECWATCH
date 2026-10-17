
import argparse
import ast
import re
from pathlib import Path


IGNORED_DIRECTORIES = {
    ".venv",
    ".git",
    "__pycache__",
}


def find_functions(source):
    """Find module-level Python functions and their required arguments."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}

    functions = {}

    # Only inspect module-level definitions. Nested functions should not
    # overwrite a module-level function with the same name.
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        args = node.args
        positional_only = args.posonlyargs
        positional_or_keyword = args.args
        positional = positional_only + positional_or_keyword

        defaults_count = len(args.defaults)
        required_count = len(positional) - defaults_count

        required_positional = [
            arg.arg for arg in positional[:required_count]
        ]

        required_keyword_only = [
            arg.arg
            for arg, default in zip(
                args.kwonlyargs,
                args.kw_defaults,
            )
            if default is None
        ]

        functions[node.name] = {
            "required_names": required_positional,
            "positional_only_names": [
                arg.arg for arg in positional_only
            ],
            "positional_names": [
                arg.arg for arg in positional
            ],
            "required_keyword_only": required_keyword_only,
        }

    return functions


def check_call(node, signature):
    """Return required arguments that appear to be missing."""
    positional_names = signature["positional_names"]
    positional_only_names = signature["positional_only_names"]
    required_names = signature["required_names"]
    required_keyword_only = signature["required_keyword_only"]

    has_starred_args = any(
        isinstance(arg, ast.Starred)
        for arg in node.args
    )

    has_kwargs_unpacking = any(
        keyword.arg is None
        for keyword in node.keywords
    )

    supplied_by_keyword = {
        keyword.arg
        for keyword in node.keywords
        if keyword.arg is not None
    }

    # Starred arguments can supply an unknown number of positional
    # arguments. Avoid unreliable positional-argument warnings.
    if has_starred_args:
        return [
            name
            for name in required_keyword_only
            if name not in supplied_by_keyword
            and not has_kwargs_unpacking
        ]

    supplied_positionally = set(
        positional_names[:len(node.args)]
    )

    missing = []

    for name in required_names:
        if name in supplied_positionally:
            continue

        if name in positional_only_names:
            missing.append(name)
        elif (
            name not in supplied_by_keyword
            and not has_kwargs_unpacking
        ):
            missing.append(name)

    for name in required_keyword_only:
        if (
            name not in supplied_by_keyword
            and not has_kwargs_unpacking
        ):
            missing.append(name)

    return missing


def scan_documentation(source, readme):
    """Scan Python code examples in README text."""
    functions = find_functions(source)
    return scan_documentation_from_functions(readme, functions)


def scan_documentation_from_functions(readme, functions):
    """Check function calls inside fenced Python examples."""
    issues = []

    pattern = re.compile(
        r"```(?:python|py|python3)\s*\n(.*?)```",
        re.IGNORECASE | re.DOTALL,
    )

    for match in pattern.finditer(readme):
        code = match.group(1)
        block_start_line = (
            readme.count("\n", 0, match.start(1)) + 1
        )

        try:
            tree = ast.parse(code)
        except SyntaxError as error:
            line = block_start_line + (error.lineno or 1) - 1
            issues.append(
                f"README.md:{line}: Invalid Python example: "
                f"{error.msg}"
            )
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            # Currently handles simple calls such as greet("Manan"),
            # not attribute calls such as service.greet("Manan").
            if not isinstance(node.func, ast.Name):
                continue

            function_name = node.func.id

            if function_name not in functions:
                continue

            missing = check_call(node, functions[function_name])

            if missing:
                line = block_start_line + node.lineno - 1
                names = ", ".join(missing)

                issues.append(
                    f"README.md:{line}: Possible missing "
                    f"argument(s) for '{function_name}': {names}"
                )

    return issues


def scan_project(project_path):
    """Scan Python files in a project and check its README."""
    project_path = Path(project_path).resolve()

    if not project_path.exists():
        return [
            f"Error: Project path does not exist: {project_path}"
        ]

    if not project_path.is_dir():
        return [
            f"Error: Project path is not a directory: {project_path}"
        ]

    readme_path = project_path / "README.md"

    if not readme_path.is_file():
        return [
            f"Error: README.md not found in {project_path}"
        ]

    try:
        readme = readme_path.read_text(encoding="utf-8")
    except OSError as error:
        return [f"Error reading README.md: {error}"]

    all_functions = {}
    duplicate_names = set()
    issues = []

    for file_path in project_path.rglob("*.py"):
        relative_path = file_path.relative_to(project_path)

        if any(
            part in IGNORED_DIRECTORIES
            for part in relative_path.parts
        ):
            continue

        try:
            source = file_path.read_text(encoding="utf-8")
        except OSError as error:
            issues.append(
                f"Warning: Could not read {relative_path}: {error}"
            )
            continue

        try:
            ast.parse(source)
        except SyntaxError as error:
            issues.append(
                f"Warning: Invalid Python in {relative_path}, "
                f"line {error.lineno}: {error.msg}"
            )
            continue

        functions = find_functions(source)

        for name, signature in functions.items():
            if name in all_functions:
                duplicate_names.add(name)
            else:
                all_functions[name] = signature

    # Skip ambiguous names rather than guessing which file's function
    # a README example intends to call.
    for name in duplicate_names:
        all_functions.pop(name, None)

    if duplicate_names:
        names = ", ".join(sorted(duplicate_names))
        issues.append(
            "Warning: Skipped function names found in multiple "
            f"Python files: {names}"
        )

    issues.extend(
        scan_documentation_from_functions(readme, all_functions)
    )

    return issues


def main():
    parser = argparse.ArgumentParser(
        description=(
            "SPECWATCH: Check Python function calls in README examples."
        )
    )

    parser.add_argument(
        "--project",
        default=".",
        help="Path to the project to scan (default: current directory).",
    )

    args = parser.parse_args()

    print(f"Scanning project: {args.project}")
    issues = scan_project(args.project)

    if issues:
        print("\nFindings:")
        for issue in issues:
            print(f"- {issue}")
    else:
        print("\nNo issues found.")

    print("\nScan complete.")


if __name__ == "__main__":
    main()
