# tester_agent.py
import dspy
import prompt
import os
import ast
from dotenv import load_dotenv
import subprocess
from architect_agent import ArchitectAgent
from developer_agent import DeveloperAgent
import numpy as np
from kmodes.kmodes import KModes
from utils import GeneratedFunction, Candidate
from colorama import Fore, Style

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
                                            function_interface=function_interface,
                                            sample_test_data=sample_test_data)
            test_program = result.test_program
            # Use ast to find whether the generated code has syntax errors
            try:
                ast.parse(test_program)
                return test_program
            except SyntaxError as e:
                print(Fore.RED + "Tester agent: generated test program Syntax Error!" + Style.RESET_ALL, e)
                error_count += 1

        print(Fore.RED + "Tester agent: ailed to generate a valid test program under error threshold." + Style.RESET_ALL)
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
    

    def main_test_func(self, generated_function: GeneratedFunction, num_test_cases: int):
        """
        Test the given function with the generated test cases.
        return a list of test results. Each element is 0 or 1:
        - 0 means passed
        - 1 means failed
        - -1 means the test program execution failed
        The length of the list is equal to the number of test cases.

        return:
        - None: If the sample test program execution failed.
        - A list of test results: If the sample test program execution passed.
        """
        print (Fore.BLUE + "Tester agent: test function:\n" + Style.RESET_ALL, generated_function.interface)
        generated_function.test_cases_num = num_test_cases

        # step 1: generate the sample test data
        sample_test_data = self.generate_sample_case(generated_function.interface)
        generated_function.sample_test_case = sample_test_data

        # step 2: generate the test program
        test_program_main = self.generate_test_program(generated_function.interface, sample_test_data)
        generated_function.function_tester_main = test_program_main

        # Use the first candidate function to make a complete test program
        test_program = generated_function.candidates[0].candidate_code + '\n' + test_program_main
        # if the generated function is a main function, add the auxiliary functions code to the test program
        if generated_function.type == "main":
            test_program = generated_function.auxiliary_functions_code + '\n' + test_program
        print (Fore.BLUE + "Tester agent: test program:\n" + Style.RESET_ALL, test_program)

        # Save and run the test program
        with open("test_program.py", "w") as f:
            f.write(test_program)
        
        result = subprocess.run(
            ['python', 'test_program.py'],
            input=sample_test_data,
            capture_output=True,
            text=True)

        if result.returncode == -1 or result.stderr != "":
            print(Fore.RED + "Tester agent: sample test program execution failed or JSON parsing failed!" + Style.RESET_ALL)
            # TODO: find out the reason why the test program failed, and improve the test program and the sample test data
            return None

        # Make sure the sample test program and the sample test data are valid here
        # step 3: generate the test cases
        test_cases = self.generate_test_cases(test_program, sample_test_data, num_test_cases)
        generated_function.test_cases = test_cases
        
        if len(test_cases) != num_test_cases:
            print(Fore.RED + "Tester agent: failed to generate the required test cases!" + Style.RESET_ALL)
            # TODO: Try to fix this issu
            return None 

        # Make sure the test cases are valid here

        print(Fore.BLUE + "Tester agent: start testing each candidates with the test cases" + Style.RESET_ALL)
        # step 4: Testing each function candidates and record the results
        test_results = []

        for candidate in generated_function.candidates:
            test_result = []
            test_program = candidate.candidate_code + '\n' + test_program_main
            # record the test program for each candidate
            candidate.candidate_tester = test_program
            # Save and run the test program
            with open("test_program.py", "w") as f:
                f.write(test_program)
            for test_case in test_cases:
                result = subprocess.run(
                    ['python', 'test_program.py'],
                    input=test_case,
                    capture_output=True,
                    text=True)
                if result.returncode == 0:
                    test_result.append(0)
                elif result.returncode == 1:
                    test_result.append(1)
                else:
                    test_result.append(-1)
            test_results.append(test_result)

            # record the test result for each candidate
            candidate.candidate_test_result = test_result
            # calculate the score for each candidate
            candidate.candidate_score = len(test_result) - sum(test_result)
        # record the test results for the generated function
        generated_function.test_results = test_results
    
    
    def cluster_test_results(self, generated_function: GeneratedFunction, cluster_num: int):
        """
        Cluster the test results into cluster_num clusters.
        """
        # Convert the test results to a numpy array
        test_results = np.array(generated_function.test_results)

        # Use KModes to cluster the test results
        km = KModes(n_clusters=cluster_num, init='Cao', n_init=5)
        clusters = km.fit_predict(test_results)

        # Record the cluster results for the generated function
        generated_function.cluster_num = cluster_num
        generated_function.cluster_results = clusters
        # Record the cluster id for each candidate
        for candidate in generated_function.candidates:
            candidate.cluster_id = clusters[candidate.candidate_index]


    def filter_candidates(self, candidates, test_results, clusters, cluster_num):

        # TODO: filter the candidates based on the clusters and the test results
        pass


    def basic_chooser(self, generated_function: GeneratedFunction):
        """
        Choose the best candidate based on the score.
        """
        best_candidate: Candidate = None
        best_score = -1
        for candidate in generated_function.candidates:
            if candidate.candidate_score > best_score:
                best_score = candidate.candidate_score
                best_candidate = candidate
        generated_function.final_candidate = best_candidate
        return best_candidate


    def test_and_choose(self, generated_functions: list[GeneratedFunction], num_test_cases: int):
        """
        Test each generated function and choose the best candidate for each function.
        """
        for generated_function in generated_functions:
            self.main_test_func(generated_function, num_test_cases)
            best_candidate = self.basic_chooser(generated_function)
            print(Fore.BLUE + "best candidate:\n" + Style.RESET_ALL, best_candidate.candidate_code)


if __name__ == "__main__":
    # Configure Language Model
    load_dotenv()
    api_key = os.environ.get('API_KEY')
    lm = dspy.LM('openai/gpt-4o-mini', api_key=api_key)
    dspy.configure(lm=lm)

    # Architect agent
    test_architect_agent = ArchitectAgent(llm=lm,
                                        analysis_prompt_template=prompt.analysis_prompt_template,
                                        generation_prompt_template=prompt.generation_prompt_template)
    
    # Developer agent
    test_developer_agent = DeveloperAgent(llm=lm,
                                        task_description=prompt.developer_agent_prompt,
                                        n=5)
    
    # Tester agent
    test_tester_agent = TesterAgent(llm=lm,
                                    tester_program_prompt=prompt.tester_program_prompt,
                                    sample_test_data_prompt=prompt.sample_test_data_prompt,
                                    test_data_gen_prompt=prompt.test_data_gen_prompt)
    
    requirements_text = (
        "Develop a modular calculator that supports addition, subtraction, multiplication, and division. "
        "The system should be divided into smaller functions to handle basic operations independently, "
        "and a main function to integrate these operations."
    )

    # Step 1: Architect agent
    analysis_text, generated_auxiliary_functions, generated_main_functions = test_architect_agent.architect(requirements_text)

    # Step 2: Developer agent
    test_developer_agent.auxiliary_developer(generated_auxiliary_functions, analysis_text, error_threshold=2)

    # step 3: tester agent test
    for generated_function in generated_auxiliary_functions:
        test_tester_agent.main_test_func(generated_function, num_test_cases=10)
        best_candidate = test_tester_agent.basic_chooser(generated_function)
        print("Best candidate:\n", best_candidate.candidate_code)
   