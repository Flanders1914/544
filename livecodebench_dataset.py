import json
import zlib
import pickle
import base64
from enum import Enum
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

class Platform(Enum):
    LEETCODE = "leetcode"
    CODEFORCES = "codeforces"
    ATCODER = "atcoder"

class Difficulty(Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class TestType(Enum):
    STDIN = "stdin"
    FUNCTIONAL = "functional"

@dataclass
class Test:
    input: str
    output: str
    testtype: TestType

    def __post_init__(self):
        self.testtype = TestType(self.testtype)

@dataclass
class CodeGenerationProblem:
    question_title: str
    question_content: str
    platform: Platform
    question_id: str
    contest_id: str
    contest_date: datetime
    starter_code: str
    difficulty: Difficulty
    public_test_cases: list[Test]
    private_test_cases: list[Test]
    metadata: dict

    def __post_init__(self):
        self.platform = Platform(self.platform)
        self.difficulty = Difficulty(self.difficulty)
        self.contest_date = datetime.fromisoformat(self.contest_date)

        self.public_test_cases = json.loads(self.public_test_cases)  # type: ignore
        self.public_test_cases = [Test(**t) for t in self.public_test_cases]

        try:
            self.private_test_cases = json.loads(self.private_test_cases)  # type: ignore
        except:
            self.private_test_cases = json.loads(
                pickle.loads(
                    zlib.decompress(
                        base64.b64decode(self.private_test_cases.encode("utf-8"))  # type: ignore
                    )
                )
            )  # type: ignore
        self.private_test_cases = [Test(**t) for t in self.private_test_cases]

        self.metadata = json.loads(self.metadata)  # type: ignore

    def insert_output(self, output_list: list[str], code_list: list[str]) -> dict:
        return {
            "question_title": self.question_title,
            "question_content": self.question_content,
            "platform": self.platform.value,
            "question_id": self.question_id,
            "contest_id": self.contest_id,
            "contest_date": self.contest_date.isoformat(),
            "starter_code": self.starter_code,
            "difficulty": self.difficulty.value,
            "output_list": output_list,
            "code_list": code_list,
        }

    def insert_output_evaluation(
        self,
        output_list: list[str],
        code_list: list[str],
        graded_list: list[bool],
        **kwargs,
    ) -> dict:
        output = self.insert_output(output_list, code_list)
        output["graded_list"] = graded_list
        output["pass@1"] = graded_list.count(True) / len(graded_list)
        for k, v in kwargs.items():
            output[k] = v
        return output

    def get_evaluation_sample(self):
        return {
            "input_output": json.dumps(
                {
                    "inputs": [
                        t.input
                        for t in self.public_test_cases + self.private_test_cases
                    ],
                    "outputs": [
                        t.output
                        for t in self.public_test_cases + self.private_test_cases
                    ],
                    "fn_name": self.metadata.get("func_name", None),
                }
            ),
        }

def filter_problems_by_platform(problems, platform_id):
    """
    Filter problems by platform
    
    Args:
        problems: List of problems
        platform_id: Platform ID (0: LeetCode, 1: CodeForces, 2: AtCoder, 3: All platforms)
    
    Returns:
        Filtered problems
    """
    if platform_id == 3:  # All platforms
        return problems
        
    platform_map = {
        0: "leetcode",
        1: "codeforces", 
        2: "atcoder"
    }
    
    platform = platform_map.get(platform_id)
    if not platform:
        return problems
        
    return [p for p in problems if p.platform.value == platform]

def load_code_generation_dataset(release_version="release_v1", start_date=None, end_date=None, platform_id=3):
    """
    Load LiveCodeBench dataset
    
    This is a mock implementation as the actual implementation requires the datasets library
    You need to install the datasets library using pip:
    pip install datasets
    """
    try:
        from datasets import load_dataset
        dataset = load_dataset("livecodebench/code_generation_lite", split="test", version_tag=release_version, trust_remote_code=True)
        dataset = [CodeGenerationProblem(**p) for p in dataset]  # type: ignore
        
        if start_date is not None:
            p_start_date = datetime.strptime(start_date, "%Y-%m-%d")
            dataset = [e for e in dataset if p_start_date <= e.contest_date]

        if end_date is not None:
            p_end_date = datetime.strptime(end_date, "%Y-%m-%d")
            dataset = [e for e in dataset if e.contest_date <= p_end_date]
            
        # Filter by platform if specified
        if platform_id != 3:
            dataset = filter_problems_by_platform(dataset, platform_id)

        print(f"Loaded {len(dataset)} problems")
        return dataset
    except ImportError:
        print("Error: datasets library not installed. Please install using: pip install datasets")
        return []
    except Exception as e:
        print(f"Error loading dataset: {e}")
        return []

def convert_problem_to_json(problem):
    """Convert a CodeGenerationProblem to a format usable by our tester"""
    public_test_cases = [
        {
            "input": t.input,
            "output": t.output,
            "testtype": t.testtype.value
        } for t in problem.public_test_cases
    ]
    
    private_test_cases = [
        {
            "input": t.input,
            "output": t.output,
            "testtype": t.testtype.value
        } for t in problem.private_test_cases
    ]
    
    return {
        "id": problem.question_id,
        "title": problem.question_title,
        "description": problem.question_content,
        "difficulty": problem.difficulty.value,
        "platform": problem.platform.value,
        "starter_code": problem.starter_code,
        "metadata": problem.metadata,
        "public_test_cases": public_test_cases,
        "private_test_cases": private_test_cases
    }

def prepare_dataset_for_tester(problems, output_path="livecodebench_prepared.json"):
    """
    Convert LiveCodeBench problems to a JSON format usable by our tester
    
    Args:
        problems: List of CodeGenerationProblem objects
        output_path: Path to write the output JSON file
        
    Returns:
        str: Path to the created JSON file
    """
    converted_problems = [convert_problem_to_json(p) for p in problems]
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(converted_problems, f, ensure_ascii=False, indent=2)
    
    print(f"Prepared dataset saved to {output_path}")
    return output_path

if __name__ == "__main__":
    # Example usage
    dataset = load_code_generation_dataset()
    if dataset:
        prepare_dataset_for_tester(dataset)
