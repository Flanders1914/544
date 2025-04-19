import argparse
import os
import time
import sys

def main():
    """
    Main function to run LiveCodeBench tests using the code generation agent
    """
    parser = argparse.ArgumentParser(description="Run tests on LiveCodeBench dataset")
    

    dataset_group = parser.add_mutually_exclusive_group(required=True)
    dataset_group.add_argument("--use-official", action="store_true", help="Use official LiveCodeBench dataset")
    dataset_group.add_argument("--dataset-path", help="Path to custom dataset file")
    parser.add_argument("--release-version", default="release_v1", help="LiveCodeBench dataset release version")
    
    # Test configuration
    parser.add_argument("--output-dir", default="livecodebench_results", help="Output directory")
    parser.add_argument("--candidate-num", type=int, default=5, help="Number of candidates to generate for each function")
    parser.add_argument("--test-case-num", type=int, default=10, help="Number of test cases for each function")
    parser.add_argument("--selector-type", type=int, default=0, choices=[0, 1], 
                       help="Selector type (0: basic selector, 1: advanced selector)")
    parser.add_argument("--cluster-num", type=int, default=3, help="Number of clusters")
    
    # Problem subset
    parser.add_argument("--max-problems", type=int, help="Maximum number of problems to test")
    parser.add_argument("--difficulty", choices=["easy", "medium", "hard"], help="Filter problems by difficulty")
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
    
    # Check if required dependencies are installed
    try:
        import tqdm
    except ImportError:
        print("Installing required dependencies...")
        os.system(f"{sys.executable} -m pip install tqdm")
    
    if args.use_official:
        try:
            import datasets
        except ImportError:
            print("Installing datasets library for official LiveCodeBench dataset...")
            os.system(f"{sys.executable} -m pip install datasets")
    
    # Build command for the tester
    cmd_parts = [sys.executable, "livecodebench_tester.py"]
    
    # Add dataset options
    if args.use_official:
        cmd_parts.append("--use-official-dataset")
        cmd_parts.extend(["--release-version", args.release_version])
    elif args.dataset_path:
        cmd_parts.extend(["--dataset", args.dataset_path])
    
    # Add test configuration
    cmd_parts.extend(["--output-dir", args.output_dir])
    cmd_parts.extend(["--candidate-num", str(args.candidate_num)])
    cmd_parts.extend(["--test-case-num", str(args.test_case_num)])
    cmd_parts.extend(["--selector-type", str(args.selector_type)])
    cmd_parts.extend(["--cluster-num", str(args.cluster_num)])
    
    # Add platform filter
    cmd_parts.extend(["--platform", str(args.platform)])
    
    # Add resume option
    if args.no_resume:
        cmd_parts.append("--no-resume")
    
    # Add problem timeout
    cmd_parts.extend(["--problem-timeout", str(args.problem_timeout)])
    
    # Add skip-problems if provided
    if args.skip_problems:
        cmd_parts.extend(["--skip-problems", args.skip_problems])

    if args.evaluate_only:
        cmd_parts.append("--evaluate-only")
    if args.force_evaluation:
        cmd_parts.append("--force-evaluation")
    
    # Set environment variable to ensure UTF-8 encoding in subprocesses
    if sys.platform == "win32":
        os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    # Execute the command
    cmd = " ".join(cmd_parts)
    print(f"Executing: {cmd}")
    return os.system(cmd)

if __name__ == "__main__":
    sys.exit(main())
