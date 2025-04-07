# tester_agent.py
import dspy
import prompt
import os
import ast
from dotenv import load_dotenv
import subprocess

class TestProgGenerationSignature(dspy.Signature):
    task_description: str =  dspy.InputField(desc="The description of your task.")
    function_interface: str = dspy.InputField(desc="The interface(a function head and docstrings) of the test function.")
    sample_test_data: str = dspy.InputField(desc="The sample test data in JSON format.")
    test_program: str = dspy.OutputField(desc="The generated program for testing.")

class SampleCaseGenerationSignature(dspy.Signature):
    task_description: str =  dspy.InputField(desc="The description of your task.")
    function_interface: str = dspy.InputField(desc="The provided interface(a function head and docstrings) of the test function.")
    sample_test_case: str = dspy.OutputField(desc="The generated sample test case.")

class TestCaseGenerationSignature(dspy.Signature):
    task_description: str =  dspy.InputField(desc="The description of your task.")
    test_program: str = dspy.InputField(desc="The provided Python test program.")
    sample_test_case: str = dspy.InputField(desc="The sample test case.")
    test_cases: list[str] = dspy.OutputField(desc="The list of generated test cases in JSON format.")


class TesterAgent(dspy.Module):
    """
    Tester Agent:
    - Receives a completed function from the Developer Agent.
    - Generate a test program for the function.
    - Generate multiple test cases in json format.
    - Run the test program with the test cases.
    """
    def __init__(self, llm, tester_program_prompt, sample_test_data_prompt, test_data_gen_prompt):
        # test_cases is a dict mapping function names to a list of test cases
        self.llm = llm
        self.tester_program_prompt = tester_program_prompt
        self.sample_test_data_prompt = sample_test_data_prompt
        self.test_data_gen_prompt = test_data_gen_prompt
        self.test_prog_gen_cot = dspy.ChainOfThought(TestProgGenerationSignature)
        self.sample_test_gen_cot = dspy.ChainOfThought(SampleCaseGenerationSignature)
        self.test_cases_gen_cot = dspy.ChainOfThought(TestCaseGenerationSignature)

    def generate_test_program(self, function_interface, sample_test_data, error_threshold=2):
        """
        Generate a test program for the given function interface.
        """
        error_count = 0
        while error_count < error_threshold:
            result = self.test_prog_gen_cot(task_description=self.tester_program_prompt,
                                            completed_function=function_interface,
                                            sample_test_data=sample_test_data)
            test_program = result.test_program
            # Use ast to find whether the generated code has syntax errors
            try:
                ast.parse(test_program)
                return test_program
            except SyntaxError as e:
                print("Generated test program Syntax Error!", e)
                error_count += 1

        print("Failed to generate a valid test program under error threshold.")
        return test_program
    

    def generate_sample_case(self, function_interface):
        """
        Generate a sample test case for the given test program.
        """
        result = self.sample_test_gen_cot(task_description=self.sample_test_data_prompt,
                                           function_interface=function_interface)
        return result.sample_test_case
        
    
    def generate_test_cases(self, test_program, sample_test_data, num_test_cases):
        """
        Generate test cases for the given test program.
        """
        test_gen_prompt = self.test_data_gen_prompt.format(num_test_cases=num_test_cases)
        result = self.test_cases_gen_cot(task_description=test_gen_prompt,
                                          test_program=test_program,
                                          sample_test_case=sample_test_data)
        return result.test_cases
    

    def main_test_func(self, function_interface, test_functions, num_test_cases):
        """
        Test the given function with the generated test cases.
        return a list of test results. Each element is 0 or 1:
        - 0 means failed
        - 1 means passed
        - -1 means the test program execution failed
        The length of the list is equal to the number of test cases.

        return:
        - None: If the sample test program execution failed.
        - A list of test results: If the sample test program execution passed.
        """
        # step 1: generate the sample test data
        sample_test_data = self.generate_sample_case(function_interface)

        # step 2: generate the test program
        test_program_main = self.generate_test_program(function_interface, sample_test_data)
        # Use the first candidate function to make a complete test program
        test_program = test_functions[0] + '\n' + test_program_main
        # Save and run the test program
        with open("test_program.py", "w") as f:
            f.write(test_program)
        
        result = subprocess.run(
            ['python', 'test_program.py'],
            input=sample_test_data,
            capture_output=True,
            text=True)

        if result.returncode != 0 or result.stdout == "-1":
            print("Sample test program execution failed or JSON parsing failed!")
            # TODO: find out the reason why the test program failed, and improve the test program and the sample test data
            return None

        # Make sure the sample test program and the sample test data are valid here
        print("Start testing the function candidates with interface:\n", function_interface)

        # step 3: generate the test cases
        test_cases = self.generate_test_cases(test_program, sample_test_data, num_test_cases)
        
        if len(test_cases) != num_test_cases:
            print("Failed to generate the required test cases!")
            # TODO: Try to fix this issu
            return None 

        # Make sure the test cases are valid here

        print("Start testing each candidates with the test cases")
        # step 4: Testing each function candidates and record the results
        test_results = []

        for candidate in test_functions:
            test_result = []
            test_program = candidate + '\n' + test_program_main
            with open("test_program.py", "w") as f:
                f.write(test_program)
            for test_case in test_cases:
                result = subprocess.run(
                    ['python', 'test_program.py'],
                    input=test_case,
                    capture_output=True,
                    text=True)

                if result.stdout == "0":
                    test_result.append(0)
                elif result.stdout == "1":
                    test_result.append(1)
                else:
                    test_result.append(-1)
            test_results.append(test_result)
        
        return test_results
    
    