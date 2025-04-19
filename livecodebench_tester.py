import os
import json
import subprocess
import argparse
import time
from pathlib import Path
import sys
import re
import signal
from tqdm import tqdm
import threading

# Check if pexpect is available (Linux/Mac), otherwise use alternative methods for Windows
try:
    import pexpect
    PEXPECT_AVAILABLE = True
except ImportError:
    PEXPECT_AVAILABLE = False

class LiveCodeBenchTester:
    """
    Class for testing code generation Agent on LiveCodeBench dataset
    """
    def __init__(self, dataset_path, output_dir=None, candidate_num=5, test_case_num=10, 
                 selector_type=0, cluster_num=3):
        """
        Initialize the tester
        
        Args:
            dataset_path: Path to the LiveCodeBench dataset
            output_dir: Output directory for storing generated code and test results
            candidate_num: Number of candidates to generate for each function
            test_case_num: Number of test cases for each function
            selector_type: Selector type (0: basic selector, 1: advanced selector)
            cluster_num: Number of clusters
        """
        self.dataset_path = dataset_path
        self.output_dir = output_dir or os.path.join(os.getcwd(), "livecodebench_results")
        self.candidate_num = candidate_num
        self.test_case_num = test_case_num
        self.selector_type = selector_type
        self.cluster_num = cluster_num
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Load dataset
        self.problems = self._load_dataset()
        
        # Load previous results if available (for resume functionality)
        self.previous_results = self._load_previous_results()
        
        # Add cache for tested code to avoid repeated testing
        self.test_cache = {}
        
        # Try to load test cache if it exists
        self.cache_path = os.path.join(self.output_dir, "test_cache.json") if output_dir else "test_cache.json"
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    self.test_cache = json.load(f)
                print(f"Loaded test cache with {len(self.test_cache)} entries from {self.cache_path}")
            except Exception as e:
                print(f"Error loading test cache: {e}")
    
    def _load_dataset(self):
        """Load LiveCodeBench dataset"""
        try:
            with open(self.dataset_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading dataset: {e}")
            return []
    
    def _load_previous_results(self):
        """Load previous test results if available"""
        results_file = os.path.join(self.output_dir, "all_results.json")
        if os.path.exists(results_file):
            try:
                with open(results_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading previous results: {e}")
        return {}
    
    def _save_test_cache(self):
        """Save the test cache to a file"""
        try:
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(self.test_cache, f, indent=2, ensure_ascii=False)
            print(f"Test cache saved with {len(self.test_cache)} entries to {self.cache_path}")
        except Exception as e:
            print(f"Error saving test cache: {e}")

    def run_main_for_problem(self, problem, problem_id, timeout=600):
        """
        Run main.py for the specified problem with timeout
        
        Args:
            problem: Problem data
            problem_id: Problem ID
            timeout: Timeout in seconds (default: 10 minutes)
        
        Returns:
            bool: Whether the execution was successful
        """
        problem_dir = os.path.join(self.output_dir, f"problem_{problem_id}")
        os.makedirs(problem_dir, exist_ok=True)
        
        # Extract problem description - support both direct "description" field and LiveCodeBench format
        description = problem.get("description", problem.get("question_content", ""))
        
        # If starter code is available, include it in the description
        starter_code = problem.get("starter_code", "")
        if (starter_code):
            description += f"\n\nStarter Code:\n```python\n{starter_code}\n```\n"
        
        # Save problem description to file
        with open(os.path.join(problem_dir, "problem.txt"), 'w', encoding='utf-8') as f:
            f.write(description)
        
        # Clean the text to remove problematic characters for subprocess
        description = self._clean_text_for_subprocess(description)
        
        # Use pexpect to automate input process if available, otherwise use subprocess
        main_py_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
        
        def run_subprocess():
            if not PEXPECT_AVAILABLE or sys.platform == "win32":
                # Use subprocess.Popen on Windows platform or when pexpect is not available
                # Explicitly set encoding to utf-8 for Windows
                proc = subprocess.Popen(
                    [sys.executable, main_py_path],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8'  # Explicitly set encoding to utf-8
                )
                
                # Provide input
                inputs = [
                    f"{self.candidate_num}\n",
                    f"{self.test_case_num}\n",
                    f"{self.selector_type}\n",
                    f"{self.cluster_num}\n",
                    f"{description}\nEND\n",
                    "Y\n"
                ]
                
                try:
                    for input_str in inputs:
                        proc.stdin.write(input_str)
                        proc.stdin.flush()
                        time.sleep(1)  # Give the program some processing time
                    
                    stdout, stderr = proc.communicate()
                except Exception as e:
                    print(f"Error during subprocess communication: {e}")
                    # Save the problematic description for debugging
                    with open(os.path.join(problem_dir, "problematic_description.txt"), 'w', encoding='utf-8') as f:
                        f.write(description)
                    return False
                
                # Log outputs for debugging
                with open(os.path.join(problem_dir, "execution_stdout.txt"), 'w', encoding='utf-8') as f:
                    f.write(stdout or "")
                if stderr:
                    with open(os.path.join(problem_dir, "execution_stderr.txt"), 'w', encoding='utf-8') as f:
                        f.write(stderr)
            else:
                # Use pexpect on Linux/Mac platform
                child = pexpect.spawn(f"python {main_py_path}")
                
                # Capture all output
                child.logfile = open(os.path.join(problem_dir, "execution_log.txt"), 'wb')
                
                # Automate input
                child.expect("Please input candidate_num")
                child.sendline(str(self.candidate_num))
                
                child.expect("Please input test_case_num")
                child.sendline(str(self.test_case_num))
                
                child.expect("Please input selector_type")
                child.sendline(str(self.selector_type))
                
                child.expect("Please input cluster_num")
                child.sendline(str(self.cluster_num))
                
                child.expect("Please input the requirements text")
                child.sendline(description + "\nEND")
                
                child.expect("Enter Y to start all agents")
                child.sendline("Y")
                
                # Wait for execution to complete
                child.expect(pexpect.EOF, timeout=600)  # 10 minutes timeout
                child.close()
            
            # Copy the final generated code
            try:
                with open("final_result.py", 'r', encoding='utf-8') as f:
                    final_code = f.read()
                    
                with open(os.path.join(problem_dir, "final_result.py"), 'w', encoding='utf-8') as f:
                    f.write(final_code)
                    
                # Copy analysis results
                if os.path.exists("analysis_text.txt"):
                    with open("analysis_text.txt", 'r', encoding='utf-8') as f:
                        analysis = f.read()
                        
                    with open(os.path.join(problem_dir, "analysis_text.txt"), 'w', encoding='utf-8') as f:
                        f.write(analysis)
                        
                return True
                
            except Exception as e:
                print(f"Error saving results: {e}")
                return False
        
        # Run the subprocess with timeout
        thread = threading.Thread(target=run_subprocess)
        thread.start()
        thread.join(timeout)
        
        if thread.is_alive():
            print(f"Timeout reached for problem {problem_id}. Skipping...")
            return False
        
        return True
    
    def _clean_text_for_subprocess(self, text):
        """
        Clean text to avoid encoding issues in subprocess
        
        Args:
            text: Input text to clean
            
        Returns:
            str: Cleaned text
        """
        # Remove non-breaking spaces and other problematic characters
        text = text.replace('\xa0', ' ')  # Replace non-breaking space with regular space
        
        # Remove other non-ASCII characters if necessary
        text = ''.join(c if ord(c) < 128 else ' ' for c in text)
        
        return text

    def evaluate_with_livecodebencher(self, problem_id, code_file, problem):
        """
        Evaluate the generated code using LiveCodeBench evaluator
        
        Args:
            problem_id: Problem ID
            code_file: Path to the generated code file
            problem: The original problem data
        
        Returns:
            dict: Evaluation results
        """
        problem_key = None
        code_hash = None
        
        # Check if we've already tested this exact code
        try:
            with open(code_file, 'r', encoding='utf-8') as f:
                code_content = f.read()
                
            # Create a hash of the code to use as a cache key
            import hashlib
            code_hash = hashlib.md5(code_content.encode('utf-8')).hexdigest()
            problem_key = f"{problem_id}_{code_hash}"
            
            # Check if we have this code in our cache - use exact key match
            if problem_key in self.test_cache:
                print(f"Using cached test results for problem {problem_id} (code hash {code_hash[:8]})")
                return self.test_cache[problem_key]
        except Exception as e:
            print(f"Error checking test cache: {e}")
            # Continue with evaluation if cache check fails
        
        print(f"No cached results found for problem {problem_id} (code hash {code_hash[:8] if code_hash else 'unknown'}), proceeding with evaluation")
        
        # If we don't have cached results, continue with normal evaluation
        # If we have the livecodebencher path set as an environment variable, use it
        livecodebencher_path = os.environ.get("LIVECODEBENCHER_PATH", "")
        
        if (livecodebencher_path and os.path.exists(livecodebencher_path)):
            try:
                result = subprocess.run(
                    [sys.executable, livecodebencher_path, "--problem-id", str(problem_id), "--code-file", code_file],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                # Parse evaluation results
                evaluation_result = json.loads(result.stdout)
                
            except Exception as e:
                print(f"Error evaluating code with external evaluator: {e}")
                evaluation_result = {"status": "error", "reason": str(e)}
        else:
            # Basic evaluation using test_program.py
            # This is a simplified evaluation that just runs the code with test cases if available
            try:
                # Extract test cases from the problem if available
                test_cases = []
                if "public_test_cases" in problem:
                    print(f"Found {len(problem['public_test_cases'])} public test cases")
                    test_cases.extend(problem['public_test_cases'])
                if "private_test_cases" in problem:
                    print(f"Found {len(problem['private_test_cases'])} private test cases")
                    test_cases.extend(problem['private_test_cases'])
                
                if not test_cases:
                    print(f"No test cases found for problem {problem_id}")
                    return {"status": "skipped", "reason": "No test cases available"}

                for test_case in test_cases:
                    if "input" not in test_case or "output" not in test_case:
                        print(f"Invalid test case format for problem {problem_id}")
                        return {"status": "error", "reason": "Invalid test case format"}
                
                # Generate test program in problem directory
                test_program_path = self._generate_test_program_for_problem(problem_id, code_file, test_cases)
                if test_program_path is None:
                    return {"status": "error", "reason": "Failed to generate test program"}
                
                # Also save test cases to problem directory
                problem_dir = os.path.join(self.output_dir, f"problem_{problem_id}")
                test_cases_path = os.path.join(problem_dir, f"test_cases_{problem_id}.json")
                with open(test_cases_path, 'w', encoding='utf-8') as f:
                    json.dump(test_cases, f, indent=2, ensure_ascii=False)
                
                # Run the test program with timeout
                try:
                    # Add 20 seconds timeout for test program execution
                    print(f"Running test program for problem {problem_id}...")
                    
                    timeout_seconds = 20  # Set an appropriate timeout value
                    
                    # Create a thread to run the subprocess
                    result_container = [None]
                    
                    def run_subprocess():
                        # Use command line parameters to limit memory usage (only effective on Unix/Linux)
                        import platform
                        env = os.environ.copy()
                        if platform.system() != "Windows":
                            # Limit memory usage to 1GB (1024MB)
                            env["PYTHONMEMORY"] = "1024"
                        
                        result_container[0] = subprocess.run(
                            [sys.executable, "-X", "utf8", test_program_path],
                            input=json.dumps(test_cases),
                            capture_output=True,
                            text=True,
                            env=env
                        )
                    
                    # Start thread
                    test_thread = threading.Thread(target=run_subprocess)
                    test_thread.daemon = True
                    test_thread.start()
                    
                    # Wait for thread to finish with timeout
                    test_thread.join(timeout=timeout_seconds)
                    
                    # Check if thread is still running (timeout occurred)
                    if test_thread.is_alive():
                        print(f"Timeout reached for test execution in problem {problem_id}. Test program took longer than {timeout_seconds} seconds.")
                        # Try to force terminate the process (if possible)
                        import psutil
                        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                            if test_program_path in str(proc.info['cmdline']):
                                try:
                                    proc.kill()
                                    print(f"Force terminated process that was running test program")
                                except:
                                    pass
                                
                        # Force garbage collection
                        import gc
                        gc.collect()
                        
                        # For timeout test cases, return all results as -1
                        all_timeout_results = [-1] * len(test_cases)
                        timeout_evaluation_result = {
                            "status": "timeout",
                            "reason": f"Test execution timeout after {timeout_seconds} seconds",
                            "stderr": "Execution timed out",
                            "stdout": json.dumps(all_timeout_results),
                            "passed_tests": 0,
                            "failed_tests": 0,
                            "error_tests": len(test_cases),
                            "total_tests": len(test_cases),
                            "success_rate": "0.00%"
                        }
                        
                        # Cache this timeout result before returning
                        if problem_key:
                            try:
                                self.test_cache[problem_key] = timeout_evaluation_result
                                print(f"Caching timeout test results for problem {problem_id} (code hash {code_hash[:8]})")
                                self._save_test_cache()
                            except Exception as e:
                                print(f"Error caching timeout test results: {e}")
                                
                        return timeout_evaluation_result
                    
                    result = result_container[0]
                    
                    # Ensure garbage collection after getting results
                    import gc
                    gc.collect()
                    
                    if not result:
                        all_error_results = [-1] * len(test_cases)
                        return {
                            "status": "error",
                            "reason": "Test execution failed with unknown error",
                            "stdout": json.dumps(all_error_results),
                            "passed_tests": 0,
                            "failed_tests": 0,
                            "error_tests": len(test_cases),
                            "total_tests": len(test_cases),
                            "success_rate": "0.00%"
                        }
                    
                    # Save test results
                    result_path = os.path.join(problem_dir, f"test_results_{problem_id}.json")
                    with open(result_path, 'w', encoding='utf-8') as f:
                        result_data = {
                            "stdout": result.stdout if hasattr(result, 'stdout') else "",
                            "stderr": result.stderr if hasattr(result, 'stderr') else "", 
                            "returncode": result.returncode if hasattr(result, 'returncode') else -1
                        }
                        json.dump(result_data, f, indent=2, ensure_ascii=False)
                    
                    # Check if the test program ran successfully
                    success = False
                    try:
                        # Try to parse the output as JSON
                        if result.stdout and result.stdout.strip():
                            test_results = json.loads(result.stdout.strip())
                            # Check if all test cases passed
                            success = all(result == 0 for result in test_results)
                            
                            # Count passed, failed, and error cases
                            passed_count = test_results.count(0)
                            failed_count = test_results.count(1)
                            error_count = test_results.count(-1)
                            
                            evaluation_result = {
                                "status": "success" if success else "failed",
                                "passed_tests": passed_count,
                                "failed_tests": failed_count,
                                "error_tests": error_count,
                                "total_tests": len(test_results),
                                "success_rate": f"{passed_count/len(test_results)*100:.2f}%",
                                "stdout": result.stdout,
                                "stderr": result.stderr,
                                "returncode": result.returncode
                            }
                        else:
                            # If stdout is empty but there's an error in stderr, classify as error
                            evaluation_result = {
                                "status": "error",
                                "reason": f"Test execution failed: {result.stderr}",
                                "stdout": result.stdout,
                                "stderr": result.stderr,
                                "returncode": result.returncode,
                                "passed_tests": 0,
                                "failed_tests": 0, 
                                "error_tests": len(test_cases),
                                "total_tests": len(test_cases),
                                "success_rate": "0.00%"
                            }
                    except Exception as e:
                        print(f"Error parsing test results: {e}")
                        evaluation_result = {
                            "status": "error",
                            "reason": f"Failed to parse test results: {e}",
                            "stdout": result.stdout,
                            "stderr": result.stderr,
                            "returncode": result.returncode
                        }
                except Exception as e:
                    print(f"Error during test execution: {e}")
                    evaluation_result = {
                        "status": "error",
                        "reason": f"Error during test execution: {e}"
                    }
            except Exception as e:
                print(f"Error during evaluation: {e}")
                evaluation_result = {"status": "error", "reason": str(e)}
        
        # After evaluation, explicitly save results to cache regardless of status
        if problem_key and 'status' in evaluation_result:
            try:
                self.test_cache[problem_key] = evaluation_result
                print(f"Caching test results for problem {problem_id} (code hash {code_hash[:8]}), status: {evaluation_result['status']}")
                self._save_test_cache()  # Always save after updating cache
            except Exception as e:
                print(f"Error caching test results: {e}")
        else:
            print(f"Warning: Unable to cache results for problem {problem_id} (missing key or status)")
            
        return evaluation_result

    def _generate_test_program_for_problem(self, problem_id, code_file, test_cases):
        """
        Generate a test program for a specific problem
        
        Args:
            problem_id: Problem ID
            code_file: Path to the code file
            test_cases: List of test cases
            
        Returns:
            str: Path to the generated test program, or None if failed
        """
        try:
            # Create problem directory path
            problem_dir = os.path.join(self.output_dir, f"problem_{problem_id}")
            os.makedirs(problem_dir, exist_ok=True)
            
            # Create the path for the test program file - save in problem directory
            test_program_path = os.path.join(problem_dir, f"test_program_{problem_id}.py")
            
            # Use the adaptive test generator
            try:
                from adaptive_test_generator import generate_adaptive_test_program
                print(f"Generating adaptive test program for problem {problem_id}...")

                if not test_cases:
                    print(f"No test cases provided for problem {problem_id}")
                    test_cases = [{
                        "input": "[]",
                        "output": "[]",
                        "testtype": "functional"
                    }]
                
                # Generate the test code directly using GPT-4o-mini
                test_program = generate_adaptive_test_program(code_file, test_cases)
                
                if test_program:
                    # Save the test program
                    with open(test_program_path, 'w', encoding='utf-8') as f:
                        f.write(test_program)
                    
                    print(f"Test program generated and saved to {test_program_path}")
                    return test_program_path
                
                print(f"Failed to generate test program for problem {problem_id}")
                    
                # Fallback: Create a basic test program that imports the original code
                with open(code_file, 'r', encoding='utf-8') as f:
                    orig_code = f.read()
                
                fallback_test = f"""
import json
import sys

# Original code from {code_file}:
{orig_code}

def main():
    try:
        test_cases = json.loads(sys.stdin.read().strip())
        results = []
        
        # Find the main function name (usually the last defined function)
        main_func_name = None
        for name, obj in globals().items():
            if callable(obj) and name not in ['main']:
                main_func_name = name
        
        if not main_func_name:
            print(json.dumps([-1] * len(test_cases)))
            return
            
        for test_case in test_cases:
            try:
                input_data = json.loads(test_case.get("input", "{{}}"))
                expected = json.loads(test_case.get("output", "null"))
                
                func = globals()[main_func_name]
                if isinstance(input_data, list):
                    result = func(*input_data)
                else:
                    result = func(input_data)
                    
                if result == expected:
                    results.append(0)
                else:
                    results.append(1)
            except Exception as e:
                results.append(-1)
                
        print(json.dumps(results))
    except Exception:
        print(json.dumps([-1]))

if __name__ == "__main__":
    main()
"""
                with open(test_program_path, 'w', encoding='utf-8') as f:
                    f.write(fallback_test)
                
                return test_program_path
                    
            except Exception as e:
                print(f"Error in test program generation: {e}")
                return None
                
        except Exception as e:
            print(f"Error generating test program: {e}")
            return None

    def _generate_stdin_stdout_test_program(self, code_file, test_cases):
        """
        Generate a simple test program specifically for stdin/stdout format problems
        
        Args:
            code_file: Path to the code file
            test_cases: List of test cases
            
        Returns:
            str: Generated test program code
        """
        try:
            with open(code_file, 'r', encoding='utf-8') as f:
                original_code = f.read()
                
            # Direct stdin/stdout test program that's simpler and more robust
            test_program = """
import json
import sys
import io
import threading
import time
from contextlib import redirect_stdout

# Original code above this point

def run_test_with_input(input_data, timeout=5):
    result = [None]
    error = [None]
    
    def target():
        try:
            # Create StringIO objects for stdin and stdout
            sys_stdin = sys.stdin
            sys_stdout = sys.stdout
            
            try:
                # Set up input
                sys.stdin = io.StringIO(input_data)
                out_buffer = io.StringIO()
                sys.stdout = out_buffer
                
                # Find and run main function or any appropriate entry point
                namespace = globals()
                if 'main' in namespace and callable(namespace['main']):
                    namespace['main']()
                elif 'solve' in namespace and callable(namespace['solve']):
                    namespace['solve']()
                else:
                    # Try to find a suitable function
                    for name, obj in namespace.items():
                        if callable(obj) and name not in ['run_test_with_input', 'target', 'main']:
                            obj()
                            break
                            
                result[0] = out_buffer.getvalue()
            finally:
                # Restore stdin and stdout
                sys.stdin = sys_stdin
                sys.stdout = sys_stdout
        except Exception as e:
            error[0] = str(e)
    
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout)
    
    if thread.is_alive():
        return None, "Execution timed out"
    if error[0]:
        return None, error[0]
    return result[0], None

def compare_output(expected, actual):
    if expected is None or actual is None:
        return False
        
    # Normalize both outputs (strip trailing newlines, convert to lines)
    expected_lines = expected.rstrip().split('\\n')
    actual_lines = actual.rstrip().split('\\n')
    
    # Filter empty lines
    expected_lines = [line for line in expected_lines if line.strip()]
    actual_lines = [line for line in actual_lines if line.strip()]
    
    if len(expected_lines) != len(actual_lines):
        return False
    
    for e_line, a_line in zip(expected_lines, actual_lines):
        if e_line.strip() != a_line.strip():
            return False
            
    return True

def main():
    # Read test cases from stdin, 
    try:
        test_cases = json.loads(sys.stdin.read().strip())
    except json.JSONDecodeError:
        print(json.dumps([-1]))
        return
    
    results = []
    
    for i, test_case in enumerate(test_cases):
        try:
            input_str = test_case.get("input", "")
            expected_output = test_case.get("output", "")
            
            # Run the test
            actual_output, error = run_test_with_input(input_str)
            
            if error:
                print(f"Error in test {i+1}: {error}", file=sys.stderr)
                results.append(-1)  # Error
                continue
            
            # Compare outputs
            if compare_output(expected_output, actual_output):
                results.append(0)  # Pass
            else:
                print(f"Test {i+1} failed:", file=sys.stderr)
                print(f"Expected:\\n{expected_output}", file=sys.stderr)
                print(f"Actual:\\n{actual_output}", file=sys.stderr)
                results.append(1)  # Fail
        except Exception as e:
            print(f"Error executing test {i+1}: {e}", file=sys.stderr)
            results.append(-1)  # Error
    
    # Output results
    print(json.dumps(results))

if __name__ == "__main__":
    main()
"""
            return f"{original_code}\n\n{test_program}"
        except Exception as e:
            print(f"Error generating stdin test program: {e}")
            return None

    def run_all_problems(self, resume=True, problem_timeout=600, evaluate_only=False, force_evaluation=False):
        """Run all problems and collect results
        
        Args:
            resume: Whether to resume from previous run
            problem_timeout: Timeout in seconds for each problem
            evaluate_only: If True, skip code generation and only evaluate existing code
            force_evaluation: If True, force re-evaluation even for already processed problems
        """
        results = self.previous_results if resume else {}
        
        for i, problem in tqdm(enumerate(self.problems), total=len(self.problems), desc="Testing problems"):
            problem_id = problem.get("id", problem.get("question_id", i))
            problem_title = problem.get("title", problem.get("question_title", f"Problem {problem_id}"))
            
            # Check if the problem is already processed
            already_processed = str(problem_id) in results
            
            # If the problem is already processed and we are resuming, skip it
            problem_dir = os.path.join(self.output_dir, f"problem_{problem_id}")
            code_file = os.path.join(problem_dir, "final_result.py")
            code_exists = os.path.exists(code_file)
            
            # Judge if we should skip this problem
            if already_processed and resume and not force_evaluation:
                print(f"\nSkipping problem {problem_id}: {problem_title} (already processed)")
                continue
            
            print(f"\nProcessing problem {problem_id}: {problem_title}")
            
            # If we are in evaluate-only mode, check if the code file exists
            success = False
            if evaluate_only:
                if code_exists:
                    print(f"Skipping code generation for problem {problem_id} (evaluate-only mode)")
                    success = True
                else:
                    print(f"Error: No code file found for problem {problem_id}. Cannot evaluate.")
                    continue
            else:
                # Run main.py to generate code
                success = self.run_main_for_problem(problem, problem_id, timeout=problem_timeout)
            
            # Before evaluating, make sure the test cache is loaded with the latest data
            if os.path.exists(self.cache_path) and not force_evaluation:
                try:
                    print(f"Reloading test cache before evaluating problem {problem_id}")
                    with open(self.cache_path, 'r', encoding='utf-8') as f:
                        self.test_cache = json.load(f)
                    print(f"Reloaded test cache has {len(self.test_cache)} entries")
                except Exception as e:
                    print(f"Error reloading test cache before problem {problem_id}: {e}")
            
            if success and os.path.exists(code_file):
                # Evaluate the generated code
                print(f"Evaluating code for problem {problem_id}")
                evaluation_result = self.evaluate_with_livecodebencher(problem_id, code_file, problem)
                results[str(problem_id)] = {
                    "success": True,
                    "title": problem_title,
                    "evaluation": evaluation_result
                }
            elif not success:
                # If code generation failed, mark as failed
                results[str(problem_id)] = {
                    "success": False,
                    "title": problem_title,
                    "error": "Code generation failed" if not evaluate_only else "No existing code file"
                }
            
            # Save intermediate results
            with open(os.path.join(self.output_dir, "all_results.json"), 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Final evaluation
        success_count = sum(1 for r in results.values() if r.get("success", False))
        perfect_score_count = sum(1 for r in results.values() 
                               if r.get("success", False) and 
                                  r.get("evaluation", {}).get("status") == "success" and
                                  r.get("evaluation", {}).get("success_rate", "0%").strip('%') == "100.00")
        
        print(f"\nOverall success rate (the proportion of successfully running problems to the total number of problems): {success_count}/{len(self.problems)} ({success_count/len(self.problems)*100:.2f}%)")
        print(f"Perfect score rate (100% success rate): {perfect_score_count}/{len(self.problems)} ({perfect_score_count/len(self.problems)*100:.2f}%)")
        
        return results

def main():
    parser = argparse.ArgumentParser(description="Test code generation Agent on LiveCodeBench dataset")
    dataset_group = parser.add_mutually_exclusive_group(required=True)
    dataset_group.add_argument("--dataset", help="Path to the LiveCodeBench dataset file")
    dataset_group.add_argument("--use-official-dataset", action="store_true", help="Use official LiveCodeBench dataset")
    
    parser.add_argument("--output-dir", help="Output directory")
    parser.add_argument("--candidate-num", type=int, default=5, help="Number of candidates to generate for each function")
    parser.add_argument("--test-case-num", type=int, default=10, help="Number of test cases for each function")
    parser.add_argument("--selector-type", type=int, default=0, choices=[0, 1], 
                        help="Selector type (0: basic selector, 1: advanced selector)")
    parser.add_argument("--cluster-num", type=int, default=3, help="Number of clusters")
    parser.add_argument("--release-version", default="release_v1", help="LiveCodeBench dataset release version")
    parser.add_argument("--platform", type=int, default=3, choices=[0, 1, 2, 3], 
                        help="Platform filter (0: LeetCode, 1: CodeForces, 2: AtCoder, 3: All platforms)")
    parser.add_argument("--no-resume", action="store_true", help="Do not resume from previous run")
    parser.add_argument("--problem-timeout", type=int, default=600, 
                       help="Timeout in seconds for each problem (default: 600)")
    parser.add_argument("--skip-problems", help="Comma-separated list of problem IDs to skip")
    parser.add_argument("--evaluate-only", action="store_true", 
                       help="Only evaluate existing generated code without regenerating")
    parser.add_argument("--force-evaluation", action="store_true",
                      help="Force re-evaluation of problems even if they were already processed")
    
    args = parser.parse_args()
    
    if args.use_official_dataset:
        # Import the dataset loader only if needed
        from livecodebench_dataset import load_code_generation_dataset, prepare_dataset_for_tester
        
        # Load and prepare dataset with platform filter
        problems = load_code_generation_dataset(
            release_version=args.release_version, 
            platform_id=args.platform
        )
        if not problems:
            print("Failed to load LiveCodeBench dataset. Please check your installation and try again.")
            return
        
        # Skip problems if specified
        if args.skip_problems:
            skip_ids = args.skip_problems.split(',')
            original_count = len(problems)
            problems = [p for p in problems if str(p.question_id) not in skip_ids]
            print(f"Skipped {original_count - len(problems)} problems")
        
        # Convert problems to the format expected by our tester
        dataset_path = prepare_dataset_for_tester(problems)
    else:
        dataset_path = args.dataset
    
    tester = LiveCodeBenchTester(
        dataset_path=dataset_path,
        output_dir=args.output_dir,
        candidate_num=args.candidate_num,
        test_case_num=args.test_case_num,
        selector_type=args.selector_type,
        cluster_num=args.cluster_num
    )
    
    tester.run_all_problems(
        resume=not args.no_resume, 
        problem_timeout=args.problem_timeout,
        evaluate_only=args.evaluate_only,
        force_evaluation=args.force_evaluation
    )

if __name__ == "__main__":
    main()
