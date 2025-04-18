import os
import json
import argparse
import subprocess
import tempfile
import shutil
from pathlib import Path
import sys

class LiveCodeBenchEvaluator:
    """
    LiveCodeBench evaluator for assessing if generated code correctly solves a problem
    """
    def __init__(self, benchmarks_dir=None):
        """
        Initialize the evaluator
        
        Args:
            benchmarks_dir: LiveCodeBench test cases directory
                           If None, will try to read from LIVECODEBENCHER_BENCHMARKS environment variable
        """
        self.benchmarks_dir = benchmarks_dir or os.environ.get("LIVECODEBENCHER_BENCHMARKS")
        
        if not self.benchmarks_dir or not os.path.exists(self.benchmarks_dir):
            raise ValueError(f"Invalid LiveCodeBench test cases directory: {self.benchmarks_dir}")
    
    def evaluate_solution(self, problem_id, code_file):
        """
        Evaluate a code solution for a specific problem
        
        Args:
            problem_id: Problem ID
            code_file: Path to the code file
            
        Returns:
            dict: Evaluation results
        """
        # Find problem test cases
        problem_dir = os.path.join(self.benchmarks_dir, str(problem_id))
        
        if not os.path.exists(problem_dir):
            return {
                "status": "error",
                "message": f"Test cases directory for problem {problem_id} not found"
            }
        
        # Create temporary working directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Copy problem files and test cases
            tests_dir = os.path.join(problem_dir, "tests")
            temp_tests_dir = os.path.join(temp_dir, "tests")
            
            if os.path.exists(tests_dir):
                shutil.copytree(tests_dir, temp_tests_dir)
            
            # Copy solution code
            solution_file = os.path.join(temp_dir, "solution.py")
            shutil.copy2(code_file, solution_file)
            
            # Find and run test script
            test_script = os.path.join(problem_dir, "test.py")
            
            if not os.path.exists(test_script):
                return {
                    "status": "error",
                    "message": f"Test script for problem {problem_id} not found"
                }
            
            try:
                # Run tests
                result = subprocess.run(
                    [sys.executable, test_script, "--solution", solution_file, "--tests", temp_tests_dir],
                    capture_output=True,
                    text=True,
                    cwd=temp_dir,
                    timeout=300  # 5 minutes timeout
                )
                
                # Try to parse JSON output
                try:
                    output = json.loads(result.stdout)
                except json.JSONDecodeError:
                    output = {
                        "stdout": result.stdout,
                        "stderr": result.stderr
                    }
                
                # Determine status based on return code
                if result.returncode == 0:
                    status = "success"
                else:
                    status = "failed"
                
                return {
                    "status": status,
                    "returncode": result.returncode,
                    "results": output
                }
                
            except subprocess.TimeoutExpired:
                return {
                    "status": "timeout",
                    "message": "Evaluation timeout (exceeded 5 minutes)"
                }
            except Exception as e:
                return {
                    "status": "error",
                    "message": str(e)
                }

def main():
    parser = argparse.ArgumentParser(description="LiveCodeBench Evaluator")
    parser.add_argument("--problem-id", required=True, help="Problem ID")
    parser.add_argument("--code-file", required=True, help="Path to code file")
    parser.add_argument("--benchmarks-dir", help="LiveCodeBench test cases directory")
    
    args = parser.parse_args()
    
    try:
        evaluator = LiveCodeBenchEvaluator(benchmarks_dir=args.benchmarks_dir)
        result = evaluator.evaluate_solution(args.problem_id, args.code_file)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}, indent=2, ensure_ascii=False))
        sys.exit(1)

if __name__ == "__main__":
    main()
