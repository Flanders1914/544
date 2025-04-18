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
        # If we have the livecodebencher path set as an environment variable, use it
        livecodebencher_path = os.environ.get("LIVECODEBENCHER_PATH", "")
        
        if livecodebencher_path and os.path.exists(livecodebencher_path):
            try:
                result = subprocess.run(
                    [sys.executable, livecodebencher_path, "--problem-id", str(problem_id), "--code-file", code_file],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                # Parse evaluation results
                return json.loads(result.stdout)
                
            except Exception as e:
                print(f"Error evaluating code with external evaluator: {e}")
                return {"status": "error", "reason": str(e)}
        else:
            # Basic evaluation using test_program.py
            # This is a simplified evaluation that just runs the code with test cases if available
            try:
                # Extract test cases from the problem if available
                test_cases = []
                if "public_test_cases" in problem:
                    test_cases.extend(problem["public_test_cases"])
                if "private_test_cases" in problem:
                    test_cases.extend(problem["private_test_cases"])
                
                if not test_cases:
                    return {"status": "skipped", "reason": "No test cases available"}
                
                # Run the test_program.py with the final_result.py
                result = subprocess.run(
                    [sys.executable, "test_program.py"],
                    input=json.dumps(test_cases),
                    capture_output=True,
                    text=True
                )
                
                return {
                    "status": "completed",
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode
                }
            except Exception as e:
                return {"status": "error", "reason": str(e)}
    
    def run_all_problems(self, resume=True, problem_timeout=600):
        """Run all problems and collect results"""
        results = self.previous_results if resume else {}
        
        for i, problem in tqdm(enumerate(self.problems), total=len(self.problems), desc="Testing problems"):
            problem_id = problem.get("id", problem.get("question_id", i))
            problem_title = problem.get("title", problem.get("question_title", f"Problem {problem_id}"))
            
            # Skip if already processed and resume is enabled
            if resume and str(problem_id) in results:
                print(f"\nSkipping problem {problem_id}: {problem_title} (already processed)")
                continue
                
            print(f"\nTesting problem {problem_id}: {problem_title}")
            
            problem_dir = os.path.join(self.output_dir, f"problem_{problem_id}")
            code_file = os.path.join(problem_dir, "final_result.py")
            
            # Run main.py to generate code
            success = self.run_main_for_problem(problem, problem_id, timeout=problem_timeout)
            
            if success and os.path.exists(code_file):
                # Evaluate the generated code
                evaluation_result = self.evaluate_with_livecodebencher(problem_id, code_file, problem)
                results[str(problem_id)] = {
                    "success": True,
                    "title": problem_title,
                    "evaluation": evaluation_result
                }
            else:
                results[str(problem_id)] = {
                    "success": False,
                    "title": problem_title,
                    "error": "Code generation failed"
                }
            
            # Save results after each problem (for resume functionality)
            with open(os.path.join(self.output_dir, "all_results.json"), 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Calculate overall success rate
        success_count = sum(1 for r in results.values() if r.get("success", False))
        print(f"\nOverall success rate: {success_count}/{len(self.problems)} ({success_count/len(self.problems)*100:.2f}%)")
        
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
    
    tester.run_all_problems(resume=not args.no_resume, problem_timeout=args.problem_timeout)

if __name__ == "__main__":
    main()
