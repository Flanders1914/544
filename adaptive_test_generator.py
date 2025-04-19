import json
import ast
import re
import os
import inspect
import signal
from functools import wraps
import threading
from dotenv import load_dotenv
import openai
import gc

class TimeoutError(Exception):
    """Exception raised when a function times out"""
    pass

def timeout_handler(timeout=5):
    """
    Decorator for handling function timeouts
    
    Args:
        timeout: Maximum execution time in seconds
        
    Returns:
        Decorated function with timeout handling
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = [TimeoutError("Function timed out")]
            
            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    result[0] = e
            
            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(timeout)
            
            if isinstance(result[0], Exception):
                raise result[0]
            return result[0]
        return wrapper
    return decorator

class AdaptiveTestGenerator:
    """
    Intelligent Test Code Generator - Generates adaptive test programs by analyzing function code and test case structures
    """
    def __init__(self, api_key=None):
        # Set up API key
        load_dotenv()
        self.api_key = api_key or os.environ.get('API_KEY')
        if not self.api_key:
            raise ValueError("API key not provided and not found in environment variables")
        
        # Initialize OpenAI client
        self.client = openai.OpenAI(api_key=self.api_key)

    def analyze_function(self, code_file):
        """
        Analyze functions in the code file, focusing on the last function as the main function
        """
        with open(code_file, 'r', encoding='utf-8') as f:
            code = f.read()
            
        try:
            # Use AST to analyze code structure
            tree = ast.parse(code)
            functions = []
            
            # Find all function definitions
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Get function parameters
                    args = [arg.arg for arg in node.args.args]
                    
                    # Get function interface (header + docstring)
                    function_interface = ast.get_source_segment(code, node).split('\n')
                    docstring_end = 0
                    
                    # Find where the docstring ends (if there is one)
                    for i, line in enumerate(function_interface):
                        if '"""' in line or "'''" in line:
                            docstring_end = i
                            if docstring_end > 0:  # If we found the end of a docstring
                                break
                    
                    # Collect only the function definition and docstring
                    if docstring_end > 0:
                        function_interface = '\n'.join(function_interface[:docstring_end+1])
                    else:
                        function_interface = function_interface[0]  # Just the function signature
                    
                    functions.append({
                        'name': node.name,
                        'args': args,
                        'interface': function_interface,
                        'line_no': node.lineno  # Store line number to find last function
                    })
            
            # Sort functions by line number to ensure we get the last one
            functions.sort(key=lambda f: f['line_no'])
            
            # The last function is the main function for the problem
            return functions[-1] if functions else None
        
        except SyntaxError as e:
            print(f"Syntax error in code file: {e}")
            return None

    def generate_test_program_with_gpt(self, function_info, sample_test_case, original_code):
        """
        Generate test program using GPT model directly.
        
        Args:
            function_info: Dictionary containing function analysis information
            sample_test_case: Sample test case for the function
            original_code: Original function code
            
        Returns:
            tuple: (test_program, imports) - Generated test program and imports
        """
        # Check if the sample test case has a special format with newlines in input
        special_format = False
        test_type = "functional"
        try:
            input_str = sample_test_case.get("input", "{}")
            test_type = sample_test_case.get("testtype", "functional")
            if "\n" in input_str:
                special_format = True
        except:
            pass

        # Prepare the prompt for GPT based on test case type
        if test_type == "stdin":
            prompt = f"""You are a highly skilled Python developer. Your task is to generate an executable Python testing program that can handle stdin/stdout style test cases. This program will be used to test a provided function or script with multiple test cases.

Context:
1. Code to test:
```python
{original_code}
```

2. Sample test case format:
{json.dumps(sample_test_case, indent=2)}

This is a stdin/stdout style test case where:
- "input" contains the text that would be fed into the stdin of the program
- "output" contains the expected text output from the program
- "testtype" is "stdin", indicating this is a stdin/stdout test

Your program should do the following:
1. Read a JSON array of test cases from standard input
2. For each test case:
   - Extract the "input" value and feed it as stdin to the program
   - Capture the program's stdout
   - Compare it with the expected "output" value
   - Record 0 for success, 1 for failure, -1 for errors or timeouts
3. Output a JSON array of results (0s, 1s, and -1s)

Implementation details:
- Use StringIO to redirect stdin/stdout
- Use threading with timeout to prevent infinite loops
- Include proper handling for setup and cleanup
- Make sure the comparison handles whitespace variations gracefully
- If a function named 'main()' exists in the code, call it; otherwise try to determine the entry point

Output two parts:
1. Additional import statements needed beyond the standard 'import json' and 'import sys'.
2. The test program code including a main() function and if __name__ == "__main__" block.

Your output should be clean Python code ready for execution without any explanation or markdown formatting.
"""
        else:
            prompt = f"""You are a highly skilled Python developer. Your task is to generate an executable Python testing program for a provided function. This program will be used to test the function with multiple test cases.

Context:
1. Function to test:
```python
{original_code}
```

2. The main function to test is: {function_info['name']}

3. Sample test case format:
{json.dumps(sample_test_case, indent=2)}

{'IMPORTANT: The input format contains a newline character "\\n" which separates multiple input arguments. You need to parse them correctly.' if special_format else ''}

Your program should do the following:
1. Read a JSON array of test cases from standard input
2. For each test case:
   - Extract the input values and expected output
   - Call the function with the appropriate inputs
   - Compare the result with the expected output
   - Record 0 for success, 1 for failure, -1 for errors or timeouts
3. Output a JSON array of results (0s, 1s, and -1s)

Implementation details:
- Handle errors and exceptions gracefully
- Use threading with timeout to prevent infinite loops
- Support various input formats (strings, lists, dictionaries)
- Support proper comparison for different output types
- If the function takes multiple parameters, unpack the input appropriately
- Make sure your code works correctly for ALL test cases in the input array

Output two parts:
1. Additional import statements needed beyond the standard 'import json' and 'import sys'.
2. The test program code including a main() function and if __name__ == "__main__" block.

Your output should be clean Python code ready for execution without any explanation or markdown formatting.
"""

        try:
            # Call the OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Use a suitable model
                messages=[
                    {"role": "system", "content": "You are a Python test code generator expert."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Lower temperature for more deterministic output
                max_tokens=2000  # Set an appropriate token limit
            )
            
            # Get the generated content
            generated_code = response.choices[0].message.content.strip()
            
            # Split imports and test program
            lines = generated_code.split('\n')
            import_lines = []
            test_program_lines = []
            
            # Extract imports
            for line in lines:
                if line.startswith('import ') or line.startswith('from '):
                    import_lines.append(line)
                else:
                    test_program_lines.append(line)
            
            imports = '\n'.join(import_lines)
            test_program = '\n'.join(test_program_lines)
            
            # Ensure we have basic imports
            if 'import json' not in imports:
                imports = 'import json\n' + imports
            if 'import sys' not in imports:
                imports = 'import sys\n' + imports
                
            return test_program, imports
            
        except Exception as e:
            print(f"Error generating test program with GPT: {e}")
            return None, None

def generate_adaptive_test_program(code_file, test_cases):
    """
    Generate an adaptive test program for the given code file and test cases
    
    Args:
        code_file: Path to the code file
        test_cases: List of test cases
        
    Returns:
        str: Generated test program code or None if failed
    """
    try:
        # Read the original code
        with open(code_file, 'r', encoding='utf-8') as f:
            original_code = f.read()
        
        # Check if this is a stdin/stdout style test case format
        is_stdin_format = False
        if test_cases and isinstance(test_cases[0], dict) and test_cases[0].get("testtype") == "stdin":
            is_stdin_format = True
            print("Detected stdin/stdout testing format")
        
        # Always use GPT to generate a test program tailored to the specific code and test cases
        return generate_generic_test_program_with_gpt(original_code, test_cases)
            
    except Exception as e:
        print(f"Error in generate_adaptive_test_program: {e}")
        try:
            with open(code_file, 'r', encoding='utf-8') as f:
                original_code = f.read()
            return generate_generic_test_program_with_gpt(original_code, test_cases)
        except:
            return generate_fallback_test_program("", test_cases)

def generate_generic_test_program_with_gpt(original_code, test_cases):
    """
    Generate a test program using GPT-4o-mini
    
    Args:
        original_code: The original code to test
        test_cases: List of test cases
        
    Returns:
        str: Generated test program code
    """
    try:
        # Initialize OpenAI
        load_dotenv()
        api_key = os.environ.get('API_KEY')
        client = openai.OpenAI(api_key=api_key)
        
        # Get sample test case
        sample_test_case = test_cases[0] if test_cases and len(test_cases) > 0 else {
            "input": "[]", 
            "output": "[]", 
            "testtype": "functional"
        }
        
        test_type = sample_test_case.get("testtype", "functional")
        
        if test_type == "stdin":
            prompt = f"""You are a highly skilled Python developer. Your task is to create a test program that can evaluate the given code with stdin/stdout style test cases.

Code to test:
```python
{original_code}
```

Sample test case:
{json.dumps(sample_test_case, indent=2)}

Create a complete Python test program that:
1. Reads a JSON array of test cases from stdin
2. For each test case, redirects stdin/stdout and runs the code
3. Compares the output with expected output and records the results (0 for success, 1 for failure, -1 for errors/timeouts)
4. Prints a JSON array of results

Implementation details:
- Use StringIO for stdin/stdout redirection
- Use threading with timeout to prevent infinite loops
- Handle different input formats properly 
- Make sure comparison handles whitespace variations correctly
- Include proper error handling
- Make sure the program works with MULTIPLE test cases, not just one
- The output MUST be a JSON array of integers (0, 1, or -1)
"""
        else:
            prompt = f"""You are a highly skilled Python developer. Your task is to create a test program that can evaluate the given code with functional test cases.

Code to test:
```python
{original_code}
```

Sample test case:
{json.dumps(sample_test_case, indent=2)}

Create a complete Python test program that:
1. Reads a JSON array of test cases from standard input
2. Identifies the main function to test from the code (usually the last one)
3. For each test case, runs the identified function with the input
4. Compares the output with expected output and records results (0 for pass, 1 for fail, -1 for errors)
5. Prints a JSON array of results

Implementation requirements:
- Handle all types of inputs (strings, lists, dictionaries, etc.)
- Use threading with timeout to prevent infinite loops or long-running code
- Implement proper error handling
- The output MUST be a JSON array of integers (0, 1, or -1)
- Make sure the program works with MULTIPLE test cases, not just one
"""
        
        # Call the OpenAI API
        print("Generating test program with GPT-4o-mini...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a Python test code generator expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2500
        )
        
        # Extract the generated code
        test_program = response.choices[0].message.content.strip()
        
        # Remove any markdown formatting
        if test_program.startswith("```python"):
            test_program = test_program[len("```python"):] 
        if test_program.endswith("```"):
            test_program = test_program[:-3]
        
        test_program = test_program.strip()
        
        # Combine with original code
        combined_code = f"{original_code}\n\n{test_program}"
        
        # Validate the code
        try:
            ast.parse(combined_code)
            print("Generated test program successfully validated")
            return combined_code
        except SyntaxError as e:
            print(f"Syntax error in generated test program: {e}")
            # Make a second attempt with a more specific prompt
            return retry_generate_test_program(original_code, test_cases, test_type)
        
    except Exception as e:
        print(f"Error in generate_generic_test_program_with_gpt: {e}")
        # Fall back to the template approach
        return generate_fallback_test_program(original_code, test_cases)

def retry_generate_test_program(original_code, test_cases, test_type):
    """
    Retry generating a test program with a more specific prompt
    
    Args:
        original_code: The original code to test
        test_cases: List of test cases
        test_type: Type of test (stdin or functional)
        
    Returns:
        str: Generated test program code
    """
    try:
        # Initialize OpenAI
        load_dotenv()
        api_key = os.environ.get('API_KEY')
        client = openai.OpenAI(api_key=api_key)
        
        prompt = f"""You are a Python test program developer. The previous test program had syntax errors. 
Create a simpler, more reliable test program for this code:

```python
{original_code}
```

Requirements:
1. Read test cases as JSON from stdin
2. For each test case, run the code with the input
3. Compare outputs and track results (0=pass, 1=fail, -1=error)
4. Print results as a JSON array of integers

Focus on creating a minimal, error-free program. Include proper error handling and timeouts.
"""
        
        # Call the OpenAI API
        print("Retrying test program generation...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a Python test code generator expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=2000
        )
        
        # Extract the generated code
        test_program = response.choices[0].message.content.strip()
        
        # Remove any markdown formatting
        if test_program.startswith("```python"):
            test_program = test_program[len("```python"):] 
        if test_program.endswith("```"):
            test_program = test_program[:-3]
        
        test_program = test_program.strip()
        
        # Combine with original code
        combined_code = f"{original_code}\n\n{test_program}"
        
        # Validate the code
        try:
            ast.parse(combined_code)
            print("Retry generated test program successfully validated")
            return combined_code
        except SyntaxError as e:
            print(f"Retry also failed with syntax error: {e}")
            # Fall back to template
            return generate_fallback_test_program(original_code, test_cases)
        
    except Exception as e:
        print(f"Error in retry_generate_test_program: {e}")
        return generate_fallback_test_program(original_code, test_cases)

def generate_fallback_test_program(original_code, test_cases=None):
    sample_test_case = test_cases[0] if test_cases and len(test_cases) > 0 else None
    
    # Check for special newline format in sample test case
    special_format = False
    if sample_test_case and isinstance(sample_test_case.get("input", ""), str):
        if "\n" in sample_test_case.get("input", ""):
            special_format = True
    
    # Basic fallback test program with improved timeout handling and memory management
    test_program = """
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
            if isinstance(input_str, str) and "\\n" in input_str:
                parts = input_str.split("\\n")
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
"""

    # Combine with original code
    if original_code:
        combined_code = f"{original_code}\n\n{test_program}"
        return combined_code
    else:
        return test_program

if __name__ == "__main__":
    # Example usage
    import sys
    if len(sys.argv) > 1:
        code_file = sys.argv[1]
        test_cases = [
            {
                "input": "[1, 2, 3]",
                "output": "6"
            }
        ]
        print(generate_adaptive_test_program(code_file, test_cases))
    else:
        print("Usage: python adaptive_test_generator.py <code_file>")