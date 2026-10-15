
import unittest

from specwatch import scan_documentation


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
        self.assertIn("invalid syntax", issues[0])


if __name__ == "__main__":
    unittest.main()
