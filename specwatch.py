
import ast
import re
from pathlib import Path


IGNORED_DIRS = {".git", ".venv", "__pycache__"}


def find_functions(source):
    """Find module-level Python functions and their required arguments."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}

    functions = {}

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

    supplied_by_keyword = {
        keyword.arg
        for keyword in node.keywords
        if keyword.arg is not None
    }

    has_unknown_kwargs = False

    for keyword in node.keywords:
        if keyword.arg is not None:
            continue

        value = keyword.value

        if not isinstance(value, ast.Dict):
            has_unknown_kwargs = True
            continue

        for key in value.keys:
            if (
                isinstance(key, ast.Constant)
                and isinstance(key.value, str)
            ):
                supplied_by_keyword.add(key.value)
            else:
                has_unknown_kwargs = True

    positional_count = 0
    has_unknown_starred_args = False

    for arg in node.args:
        if not isinstance(arg, ast.Starred):
            positional_count += 1
            continue

        value = arg.value

        if isinstance(value, (ast.List, ast.Tuple)):
            positional_count += len(value.elts)
        else:
            has_unknown_starred_args = True

    if has_unknown_starred_args:
        return [
            name
            for name in required_keyword_only
            if name not in supplied_by_keyword
            and not has_unknown_kwargs
        ]

    supplied_positionally = set(
        positional_names[:positional_count]
    )

    missing = []

    for name in required_names:
        if name in supplied_positionally:
            continue

        if name in positional_only_names:
            missing.append(name)
        elif (
            name not in supplied_by_keyword
            and not has_unknown_kwargs
        ):
            missing.append(name)

    for name in required_keyword_only:
        if (
            name not in supplied_by_keyword
            and not has_unknown_kwargs
        ):
            missing.append(name)

    return missing


def find_duplicate_arguments(node, signature):
    """Find arguments supplied more than once in a function call."""
    positional_names = signature["positional_names"]
    positional_only_names = set(signature["positional_only_names"])

    keyword_names = [
        keyword.arg
        for keyword in node.keywords
        if keyword.arg is not None
    ]

    duplicates = []

    # Detect a keyword name repeated more than once.
    for name in keyword_names:
        if keyword_names.count(name) > 1 and name not in duplicates:
            duplicates.append(name)

    # Dynamic starred arguments make positional binding uncertain.
    if any(isinstance(arg, ast.Starred) for arg in node.args):
        return duplicates

    # Detect parameters supplied both positionally and by keyword.
    for index, _arg in enumerate(node.args):
        if index >= len(positional_names):
            break

        name = positional_names[index]

        if (
            name not in positional_only_names
            and name in keyword_names
            and name not in duplicates
        ):
            duplicates.append(name)

    return duplicates


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

            # Only simple calls such as greet("Manan") are supported.
            if not isinstance(node.func, ast.Name):
                continue

            function_name = node.func.id

            if function_name not in functions:
                continue

            signature = functions[function_name]
            line = block_start_line + node.lineno - 1

            duplicates = find_duplicate_arguments(node, signature)

            if duplicates:
                names = ", ".join(duplicates)
                issues.append(
                    f"README.md:{line}: Invalid call to "
                    f"'{function_name}': multiple values for "
                    f"argument(s) {names}"
                )

            missing = check_call(node, signature)

            if missing:
                names = ", ".join(missing)
                issues.append(
                    f"README.md:{line}: Possible missing "
                    f"argument(s) for '{function_name}': {names}"
                )

    return issues


def scan_project(project_path):
    """Scan Python files in a project and check README examples."""
    project_path = Path(project_path)
    readme_path = project_path / "README.md"

    if not readme_path.exists():
        return [f"README.md not found in {project_path}"]

    try:
        readme = readme_path.read_text(encoding="utf-8")
    except OSError as error:
        return [f"Could not read README.md: {error}"]

    functions = {}
    duplicate_names = set()
    issues = []

    for path in project_path.rglob("*.py"):
        if any(part in IGNORED_DIRS for part in path.parts):
            continue

        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        file_functions = find_functions(source)

        for name, signature in file_functions.items():
            if name in functions:
                duplicate_names.add(name)
            else:
                functions[name] = signature

    for name in sorted(duplicate_names):
        issues.append(
            f"Warning: duplicate top-level function name '{name}' "
            "found in multiple Python files; README checks may be "
            "ambiguous."
        )

    issues.extend(scan_documentation_from_functions(readme, functions))
    return issues
