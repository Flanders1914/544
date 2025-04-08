def calculate(operation: str, a: float, b: float) -> float:
    """
    Performs a calculation based on the specified operation and operands.

    Parameters:
    operation (str): The operation to perform ('add', 'subtract', 'multiply', 'divide').
    a (float): The first operand.
    b (float): The second operand.

    Returns:
    float: The result of the calculation.

    Raises:
    ValueError: If the operation is not recognized.

    Example:
    >>> calculate('add', 1, 2)
    3
    >>> calculate('divide', 10, 0)
    ValueError: Division by zero is not allowed.
    """
    if operation == 'add':
        return add(a, b)
    elif operation == 'subtract':
        return subtract(a, b)
    elif operation == 'multiply':
        return multiply(a, b)
    elif operation == 'divide':
        return divide(a, b)
    else:
        raise ValueError(f"Operation '{operation}' is not recognized.")
import json
import sys

def main():
    # Read JSON input from standard input
    input_data = sys.stdin.read()
    
    try:
        # Parse the JSON data
        test_cases = json.loads(f'[{input_data}]')  # Wrapping in brackets to form a valid JSON array
    except json.JSONDecodeError:
        sys.exit(-1)

    for test_case in test_cases:
        operation = test_case['operation']
        a = test_case['a']
        b = test_case['b']
        expected_result = test_case['expected_result']
        
        try:
            # Call the function with the test case data
            result = calculate(operation, a, b)
            # Check if the result matches the expected result
            if result != expected_result:
                sys.exit(1)
        except Exception as e:
            # Check if the exception message matches the expected result
            if str(e) != expected_result:
                sys.exit(1)

    # If all tests pass
    sys.exit(0)

if __name__ == "__main__":
    main()