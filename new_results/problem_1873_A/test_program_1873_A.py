import sys
from typing import List
def can_transform_to_abc(s: str) -> str:
    """
    Checks if the string `s` can be transformed into 'abc' by swapping at most one pair of characters.

    Parameters:
    s (str): A string containing the characters 'a', 'b', and 'c' in some order.

    Returns:
    str: 'YES' if the transformation is possible, 'NO' otherwise.

    Example:
    >>> can_transform_to_abc('acb')
    'YES'
    """
    # The target string we want to achieve
    target = "abc"
    
    # If the string is already 'abc', return 'YES'
    if s == target:
        return "YES"
    
    # Count the number of characters that are out of place
    mismatch_count = sum(1 for i in range(3) if s[i] != target[i])
    
    # If there are exactly two mismatches, we can swap them to get 'abc'
    if mismatch_count == 2:
        return "YES"
    
    # In all other cases, return 'NO'
    return "NO"

def process_test_cases(t: int, cases: List[str]) -> List[str]:
    """
    Processes multiple test cases to determine if each string can be transformed into 'abc' with at most one swap.

    Parameters:
    t (int): The number of test cases.
    cases (List[str]): A list of strings, each containing the characters 'a', 'b', and 'c'.

    Returns:
    List[str]: A list of results for each test case, either 'YES' or 'NO'.

    Example:
    >>> process_test_cases(3, ['abc', 'acb', 'bac'])
    ['YES', 'YES', 'YES']
    """
    results = []
    for case in cases:
        result = can_transform_to_abc(case)
        results.append(result)
    return results


import json
import sys
import inspect
import threading
import time
import gc

# Original code is included before this point

# Timeout exception class
class TimeoutError(Exception):
    pass

# Timeout decorator with stricter timeout handling
def timeout_handler(func, timeout=5):
    def wrapper(*args, **kwargs):
        result = [TimeoutError("Function call timed out")]
        completed = [False]
        
        def target():
            try:
                result[0] = func(*args, **kwargs)
                completed[0] = True
            except Exception as e:
                result[0] = e
                completed[0] = True
                
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        
        # Set a start time and monitor the thread
        start_time = time.time()
        max_wait_time = min(timeout, 10)  # Maximum wait time of 10 seconds to prevent hanging
        while not completed[0] and time.time() - start_time < max_wait_time:
            time.sleep(0.1)  # Small sleep to avoid CPU hogging
        
        if not completed[0]:
            # If the thread is still running after timeout, terminate it
            gc.collect()
            return TimeoutError("Function call timed out")
        
        if isinstance(result[0], Exception):
            raise result[0]
        return result[0]
    
    return wrapper

def main():
    # Set a global timeout for the entire test process
    start_time = time.time()
    max_total_time = 12  # Maximum total time in seconds for all tests (reduced from 15)
    
    # Enable garbage collection at start
    gc.collect()
    
    # Read test cases from stdin
    try:
        input_data = sys.stdin.read().strip()
        test_cases = json.loads(input_data)
    except json.JSONDecodeError:
        print("Failed to parse test cases", file=sys.stderr)
        sys.exit(-1)
    
    # Find the main function to test (usually the last defined function)
    main_function = None
    main_func_obj = None
    
    for name, obj in globals().items():
        if callable(obj) and name not in ['main', 'generate_fallback_test_program', 'timeout_handler', 'TimeoutError'] and inspect.isfunction(obj):
            # Prefer the last defined function
            main_function = name
            main_func_obj = obj
    
    if not main_function:
        # If no function found, report all tests as failed
        print(json.dumps([-1] * len(test_cases)))
        return
    
    # Wrap the function with timeout handler
    wrapped_func = timeout_handler(main_func_obj, timeout=3)
    
    # Determine function parameter count for better calling convention
    param_count = len(inspect.signature(main_func_obj).parameters)
    
    results = []
    for i, test_case in enumerate(test_cases):
        # Periodically check total time and perform garbage collection
        if i > 0 and (i % 3 == 0 or time.time() - start_time > max_total_time - 3):
            gc.collect()
            
        # Check if we're approaching total time limit
        if time.time() - start_time > max_total_time:
            # If we're out of time, mark remaining tests as timeout
            remaining = len(test_cases) - i
            print(f"Total time limit reached. Marking {remaining} remaining tests as timeouts.", file=sys.stderr)
            results.extend([-1] * remaining)
            break
        
        try:
            # Extract input and expected output - make sure to handle dict case properly
            if not isinstance(test_case, dict):
                print(f"Unexpected test case format: {type(test_case).__name__}", file=sys.stderr)
                results.append(-1)
                continue
                
            input_str = test_case.get("input", "{}")
            expected_output_str = test_case.get("output", "null")
            
            # Parse expected output
            try:
                expected_output = json.loads(expected_output_str)
            except json.JSONDecodeError:
                expected_output = expected_output_str
            
            result = None
            # Special handling for input with newline separators
            if isinstance(input_str, str) and "\n" in input_str:
                parts = input_str.split("\n")
                args = []
                for part in parts:
                    try:
                        # Try to parse each part as JSON
                        args.append(json.loads(part))
                    except json.JSONDecodeError:
                        # If not valid JSON, use as string
                        args.append(part)
                
                # Call the function with the parsed arguments and timeout protection
                result = wrapped_func(*args)
            else:
                # Standard parsing if no newlines
                try:
                    input_data = json.loads(input_str)
                    
                    # Call the function based on parameter count and input type with timeout protection
                    if isinstance(input_data, list):
                        # If function has only one parameter, pass the list as a single argument
                        if param_count == 1:
                            result = wrapped_func(input_data)
                        else:
                            # Function likely expects multiple parameters
                            result = wrapped_func(*input_data)
                    elif isinstance(input_data, dict):
                        # Try keyword arguments if dictionary
                        try:
                            result = wrapped_func(**input_data)
                        except TypeError:
                            # Fall back to passing dict as single argument
                            result = wrapped_func(input_data)
                    else:
                        # Single value input
                        result = wrapped_func(input_data)
                except json.JSONDecodeError:
                    # If not valid JSON, use as raw string
                    result = wrapped_func(input_str)
            
            # Compare result with expected output
            if isinstance(expected_output, (int, float)) and isinstance(result, (int, float)):
                # Use approximate equality for floating point
                is_equal = abs(result - expected_output) < 1e-9
            else:
                is_equal = result == expected_output
            
            results.append(0 if is_equal else 1)
            
            # Clean up variables to free memory
            del input_str, expected_output_str
            if 'input_data' in locals():
                del input_data
            if 'parts' in locals():
                del parts
            if 'args' in locals():
                del args
                
            # Force garbage collection after each test case to free up memory
            gc.collect()
            
        except TimeoutError:
            print(f"Error executing test: Function execution timed out", file=sys.stderr)
            results.append(-1)
        except Exception as e:
            print(f"Error executing test: {e}", file=sys.stderr)
            results.append(-1)
    
    # Output results as JSON array
    print(json.dumps(results))
    
    # Final garbage collection before exiting
    gc.collect()

if __name__ == "__main__":
    # Set up signal handler for timeouts
    gc.set_debug(gc.DEBUG_STATS)
    # Set garbage collection thresholds to avoid memory issues
    gc.set_threshold(100, 10, 10)
    
    main()
    
    # Final cleanup
    gc.collect()
