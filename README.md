
# SPECWATCH

**Catch missing arguments in Python documentation examples before your readers do.**

SPECWATCH is a lightweight, rule-based Python tool that checks code examples in Markdown documentation against function definitions in the source code.

It looks for potential missing required arguments and certain invalid function calls. The project uses Python's built-in Abstract Syntax Tree (AST) module instead of executing documentation examples.

## Why I built this

Documentation examples are easy to overlook when a function changes. A function may require two arguments while its README still shows a call with only one.

SPECWATCH explores a simple idea: can we use Python's syntax tree to catch some of these mismatches automatically?

This is a small static-analysis project, not a replacement for a full Python type checker or linter.

## Features

- Finds module-level Python function definitions and their required parameters.
- Scans fenced Python examples in Markdown files.
- Reports potentially missing required arguments.
- Handles required keyword-only arguments.
- Inspects literal list and tuple unpacking, such as `func(*[1, 2])`.
- Inspects literal dictionary unpacking, such as `func(**{"name": "Manan"})`.
- Detects certain duplicate positional and keyword argument combinations.
- Reports syntax errors in fenced Python examples.
- Includes unit tests and a benchmark script.

## Example

Suppose your source code defines:

```python
def greet(name, greeting):
    return f"{greeting}, {name}!"
```

But your README contains:

```python
greet("Manan")
```

SPECWATCH can report a potential missing argument:

```text
README.md:2: Possible missing argument(s) for 'greet': greeting
```

The corrected example is:

```python
greet("Manan", "Hello")
```

## Requirements

- Python 3.10 or newer is recommended.
- Git is optional if you only want to run the project locally.

SPECWATCH currently uses Python's standard library, so no third-party package installation is required.

## Installation

Clone the repository:

```bash
git clone https://github.com/MananCodes-Dev/SPECWATCH.git
cd SPECWATCH
```

Create and activate a virtual environment if you want an isolated development setup.

**Windows PowerShell:**

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

The project can also be run with an existing Python environment.

## Usage

### Run the unit tests

```powershell
python -m unittest -v
```

### Run the benchmark

```powershell
python benchmark_specwatch.py
```

### Use SPECWATCH in Python

The current API can scan source code against README text:

```python
from specwatch import scan_documentation

source = """
def greet(name, greeting):
    return f"{greeting}, {name}!"
"""

readme = '''
```python
greet("Manan")
```
'''

issues = scan_documentation(source, readme)

for issue in issues:
    print(issue)
```

### Scan a project directory

The project scanner looks for a `README.md` and Python files in the target directory.

```python
from specwatch import scan_project

issues = scan_project("path/to/your/project")

for issue in issues:
    print(issue)
```

The scanner is a prototype. Review its findings rather than treating every result as a definitive Python runtime error.

## How it works

1. **Parse the source:** Python's `ast` module reads function definitions without executing the source code.
2. **Collect signatures:** SPECWATCH records required positional parameters, positional-only parameters, and required keyword-only parameters for supported module-level functions.
3. **Read Markdown examples:** It finds fenced blocks marked `python`, `py`, or `python3`.
4. **Inspect function calls:** It compares supported calls in those examples with the collected signatures.
5. **Report findings:** It prints potential missing arguments and selected invalid-call warnings with README line numbers.

## Tests and benchmark

The project includes a unit-test suite and a separate benchmark script.

The latest recorded results were:

- **18 unit tests passed.**
- **22 benchmark cases classified as expected.**
- **0 false positives and 0 false negatives** on those 22 hand-picked benchmark cases.

These results apply only to the current test set. They do not establish 100% accuracy on arbitrary Python projects. The benchmark is small and uses deliberately selected examples.

Run the tests yourself to verify the current checkout:

```powershell
python -m unittest -v
python benchmark_specwatch.py
```

## Current limitations

SPECWATCH does not implement Python's complete name-resolution or argument-binding rules.

- It currently focuses on simple function calls such as `greet("Manan")`; attribute calls such as `service.greet("Manan")` are not analyzed.
- Function signatures are collected from module-level definitions. Imported functions and class methods are not resolved.
- Dynamic argument unpacking, such as `func(*args)` or `func(**kwargs)`, cannot always be analyzed statically.
- Some invalid calls may be reported as missing arguments rather than receiving a precise explanation of the underlying error.
- The analyzer does not execute examples or prove that they work.
- Duplicate function names across files can make signature selection ambiguous.

These are known boundaries of the current implementation, not problems that the tool claims to have solved.

## Roadmap

- [ ] Improve diagnostics for positional-only arguments passed by keyword.
- [ ] Expand tests for Python's argument-binding rules.
- [ ] Improve benchmark assertions so they verify warning types, not just whether a warning exists.
- [ ] Reduce false positives and false negatives on a broader test set.
- [ ] Explore support for imported functions and attribute calls.
- [ ] Add automated checks for documentation examples in continuous integration.

## Tech stack

- Python
- `ast` for syntax-tree inspection
- `unittest` for automated tests
- Git and GitHub for version control

## Contributing

Issues, reproducible examples, and focused improvements are welcome.

If you find a case where SPECWATCH misses a problem or reports a warning incorrectly, include a minimal Python function definition, the documentation example, and the expected result.

## License

No license has been specified yet. Check the repository for a `LICENSE` file before reusing or distributing this project.
