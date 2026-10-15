
from specwatch import scan_documentation


SOURCE = """
def greet(name, greeting):
    return f"{greeting}, {name}!"

def add(a, b):
    return a + b

def welcome(name, greeting="Hello"):
    return f"{greeting}, {name}!"

def create_user(name, *, role):
    return name, role

def collect(first, *items):
    return first, items

def configure(name, **options):
    return name, options
"""


CASES = [
    {
        "name": "Missing required argument",
        "code": 'greet("Manan")',
        "should_warn": True,
    },
    {
        "name": "Correct positional call",
        "code": 'greet("Manan", "Hello")',
        "should_warn": False,
    },
    {
        "name": "Correct keyword call",
        "code": 'greet(name="Manan", greeting="Hello")',
        "should_warn": False,
    },
    {
        "name": "Missing second argument",
        "code": "add(5)",
        "should_warn": True,
    },
    {
        "name": "Optional argument omitted",
        "code": 'welcome("Manan")',
        "should_warn": False,
    },
    {
        "name": "Missing keyword-only argument",
        "code": 'create_user("Manan")',
        "should_warn": True,
    },
    {
        "name": "Positional-only argument supplied incorrectly",
        "code": 'def example():\n    pass\n',
        "should_warn": False,
    },
    {
        "name": "Variadic positional argument",
        "code": 'collect("first", 2, 3, 4)',
        "should_warn": False,
    },
    {
        "name": "Optional keyword arguments",
        "code": 'configure("app", debug=True)',
        "should_warn": False,
    },
    {
        "name": "List unpacking in a call",
        "code": "add(*[1, 2])",
        "should_warn": False,
    },
]


def main():
    true_positive = 0
    true_negative = 0
    false_positive = 0
    false_negative = 0

    print("SPECWATCH Expanded Benchmark")
    print("=" * 45)

    for case in CASES:
        readme = (
            "```python\n"
            + case["code"]
            + "\n```\n"
        )

        findings = scan_documentation(SOURCE, readme)
        detected = bool(findings)
        expected = case["should_warn"]

        if expected and detected:
            result = "TRUE POSITIVE"
            true_positive += 1
        elif not expected and not detected:
            result = "TRUE NEGATIVE"
            true_negative += 1
        elif not expected and detected:
            result = "FALSE POSITIVE"
            false_positive += 1
        else:
            result = "FALSE NEGATIVE"
            false_negative += 1

        print(f"\n{case['name']}: {result}")

        for finding in findings:
            print(f"  {finding}")

    total = len(CASES)
    correct = true_positive + true_negative
    accuracy = correct / total * 100

    print("\n" + "=" * 45)
    print(f"Total cases:      {total}")
    print(f"True positives:   {true_positive}")
    print(f"True negatives:   {true_negative}")
    print(f"False positives:  {false_positive}")
    print(f"False negatives:  {false_negative}")
    print(f"Accuracy:         {accuracy:.1f}%")

    if true_positive + false_positive:
        precision = (
            true_positive / (true_positive + false_positive) * 100
        )
        print(f"Precision:        {precision:.1f}%")

    if true_positive + false_negative:
        recall = (
            true_positive / (true_positive + false_negative) * 100
        )
        print(f"Recall:           {recall:.1f}%")


if __name__ == "__main__":
    main()
