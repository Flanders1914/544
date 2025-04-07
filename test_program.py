def add(a: float, b: float) -> float:
    """
    Performs addition of two numbers.

    Parameters:
    a (float): The first number.
    b (float): The second number.

    Returns:
    float: The sum of a and b.

    Example:
    >>> add(2, 3)
    5
    """
    return a + b
import json
import sys

def main():
    # Read JSON input from standard input
    input_data = sys.stdin.read()
    
    # Parse the JSON data
    try:
        test_data = json.loads(input_data)
    except json.JSONDecodeError:
        sys.exit(-1)

    # Extract test inputs and expected output
    a = test_data.get("a")
    b = test_data.get("b")
    expected_result = test_data.get("sum_result")

    # Call the function to test (the actual function will be provided by the backend)
    actual_result = add(a, b)

    # Check if the actual result matches the expected result
    if actual_result == expected_result:
        sys.exit(0)  # Test passed
    else:
        sys.exit(1)  # Test failed

if __name__ == "__main__":
    main()