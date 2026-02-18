def average(numbers: list[int | float]) -> float:
    """Calculate the average of a list of numbers.

    Args:
        numbers (list[int | float]): A list of integers or floats.

    Returns:
        float: The average of the numbers in the list.
    """
    if not numbers:
        raise ValueError("The list of numbers is empty.")
    
    total = sum(numbers)
    count = len(numbers)
    return total / count

def add(a: int | float, b: int | float) -> int | float:
    return a + b

def subtract(a: int | float, b: int | float) -> int | float:
    return a - b

def multiply(a: int | float, b: int | float) -> int | float:
    return a * b
