
def calculate_average(marks, bonus):
    """Calculate and return the average of a list of marks."""
    if len(marks) == 0:
        raise ValueError("Marks cannot be empty")

    return sum(marks) / len(marks) + bonus


print(calculate_average([80, 90], 5))
