
import tempfile
import unittest
from pathlib import Path

from specwatch import scan_documentation, scan_project


class TestSpecwatch(unittest.TestCase):

    def setUp(self):
        self.source = """
def calculate_average(marks, bonus):
    return sum(marks) / len(marks) + bonus
"""

    def test_detects_missing_argument(self):
        readme = """
```python
calculate_average([80, 90])
```
"""
        issues = scan_documentation(self.source, readme)

        self.assertEqual(len(issues), 1)
        self.assertIn("bonus", issues[0])

    def test_accepts_correct_call(self):
        readme = """
```python
calculate_average([80, 90], 5)
```
"""
        issues = scan_documentation(self.source, readme)

        self.assertEqual(issues, [])

    def test_accepts_keyword_argument(self):
        readme = """
```python
calculate_average([80, 90], bonus=5)
```
"""
        issues = scan_documentation(self.source, readme)

        self.assertEqual(issues, [])

    def test_accepts_optional_argument(self):
        source = """
def greet(name, greeting="Hello"):
    return f"{greeting}, {name}"
"""
        readme = """
```python
greet("Manan")
```
"""
        issues = scan_documentation(source, readme)

        self.assertEqual(issues, [])

    def test_detects_missing_keyword_only_argument(self):
        source = """
def create_user(name, *, role):
    return name, role
"""
        readme = """
```python
create_user("Manan")
```
"""
        issues = scan_documentation(source, readme)

        self.assertEqual(len(issues), 1)
        self.assertIn("role", issues[0])

    def test_reports_invalid_python_example(self):
        readme = """
```python
calculate_average(
```
"""
        issues = scan_documentation(self.source, readme)

        self.assertEqual(len(issues), 1)
        self.assertIn("Invalid Python example", issues[0])

    def test_reports_readme_line_number(self):
        source = """
def greet(name, greeting):
    return f"{greeting}, {name}"
"""
        readme = (
            "# Demo\n"
            "\n"
            "```python\n"
            'greet("Manan")\n'
            "```\n"
        )

        issues = scan_documentation(source, readme)

        self.assertEqual(len(issues), 1)
        self.assertIn("README.md:4:", issues[0])

    def test_scans_project_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)

            (project / "example.py").write_text(
                'def greet(name, greeting):\n'
                '    return f"{greeting}, {name}"\n',
                encoding="utf-8",
            )

            (project / "README.md").write_text(
                "# Demo\n"
                "\n"
                "```python\n"
                'greet("Manan")\n'
                "```\n",
                encoding="utf-8",
            )

            issues = scan_project(project)

            self.assertEqual(len(issues), 1)
            self.assertIn("greeting", issues[0])

    def test_reports_missing_readme(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            issues = scan_project(temp_dir)

            self.assertEqual(len(issues), 1)
            self.assertIn("README.md not found", issues[0])


    def test_detects_missing_positional_only_argument(self):
        source = '''
def greet(name, /, greeting="Hello"):
    return f"{greeting}, {name}!"
'''
        readme = '''
```python
greet(name="Manan")
```
'''
        issues = scan_documentation(source, readme)

        self.assertEqual(len(issues), 1)
        self.assertIn("name", issues[0])


    def test_warns_about_duplicate_function_names(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)

            (project / "first.py").write_text(
                "def greet(name):\n"
                "    return name\n",
                encoding="utf-8",
            )

            (project / "second.py").write_text(
                "def greet(name, greeting):\n"
                "    return greeting, name\n",
                encoding="utf-8",
            )

            (project / "README.md").write_text(
                "# Demo\n\n"
                "```python\n"
                'greet("Manan")\n'
                "```\n",
                encoding="utf-8",
            )

            issues = scan_project(project)

            self.assertTrue(
                any(
                    "multiple Python files" in issue
                    and "greet" in issue
                    for issue in issues
                )
            )



    def test_accepts_starred_positional_arguments(self):
        source = """
def add(a, b):
    return a + b
"""
        readme = """
```python
add(*[1, 2])
```
"""
        issues = scan_documentation(source, readme)

        self.assertEqual(issues, [])


    def test_accepts_dictionary_unpacking(self):
        source = """
def greet(name, greeting):
    return f"{greeting}, {name}!"
"""
        readme = '''
```python
greet(**{"name": "Manan", "greeting": "Hello"})
```
'''
        issues = scan_documentation(source, readme)

        self.assertEqual(issues, [])


    def test_detects_missing_argument_in_nested_call(self):
        source = """
def greet(name, greeting):
    return f"{greeting}, {name}!"
"""
        readme = '''
```python
greet(str("Manan"))
```
'''
        issues = scan_documentation(source, readme)

        self.assertEqual(len(issues), 1)
        self.assertIn("greeting", issues[0])


    def test_nested_function_does_not_override_module_function(self):
        source = """
def greet(name, greeting):
    return f"{greeting}, {name}!"

def wrapper():
    def greet(name):
        return name
"""
        readme = '''
```python
greet("Manan")
```
'''
        issues = scan_documentation(source, readme)

        self.assertEqual(len(issues), 1)
        self.assertIn("greeting", issues[0])


    def test_nested_function_does_not_override_module_function(self):
        source = """
def greet(name, greeting):
    return f"{greeting}, {name}!"

def wrapper():
    def greet(name):
        return name
"""
        readme = '''
```python
greet("Manan")
```
'''
        issues = scan_documentation(source, readme)

        self.assertEqual(len(issues), 1)
        self.assertIn("greeting", issues[0])



if __name__ == "__main__":
    unittest.main()
