# developer_agent.py
import dspy
from dotenv import load_dotenv
from architect_agent import ArchitectAgent
import prompt
import os
import ast

class DeveloperSignature(dspy.Signature):
    task_description: str =  dspy.InputField(desc="The description of your task.")
    architecture_analysis: str = dspy.InputField(desc="Detailed analysis of the program architecture.")
    function_interface: str = dspy.InputField(desc="The interface(function head and docstrings) of the incomplete function.")
    generate_function: str = dspy.OutputField(desc="The complete function code based on the function interface.")

class DeveloperAgent(dspy.Module):
    """
    Developer Agent:
    - Receives function interfaces from the Architect Agent.
    - Generates multiple candidate implementations for each function.
    - Uses dspy's Chain-of-Thought to interact with the LLM for code generation.
    """
    def __init__(self, llm, task_description, n):
        self.llm = llm
        self.task_description = task_description
        # number of candidates
        self.n = n
        # Initialize a chain-of-thought module for coding reasoning
        self.developer_cot = dspy.ChainOfThought(DeveloperSignature)

    def generate_candidates(self, function_interface, architecture_analysis, error_threshold=2):
        """
        Generate multiple candidate implementations for a given function interface.
        Test the generated code has syntax errors or not.
        - If has syntax errors, try again until reaching the number of error_threshold.
        Returns a list of candidate code implementations.
        """
        candidates = []
        # Generate multiple candidates
        count = 0
        error_count = 0
        while count < self.n:
            result = self.developer_cot(task_description=self.task_description,
                                      architecture_analysis=architecture_analysis,
                                      function_interface=function_interface)
            candidate = result.generate_function
            
            # Use ast to find whether the generated code has syntax errors
            try:
                ast.parse(candidate)
            except SyntaxError as e:
                print("Generated function Syntax Error!", e)
                error_count += 1
                if error_count < error_threshold:
                    continue
                    
            count += 1
            candidates.append(candidate)
            # clean the error_count
            error_count = 0

        return candidates
    

if __name__ == "__main__":
    # Configure Language Model
    load_dotenv()
    api_key = os.environ.get('API_KEY')
    lm = dspy.LM('openai/gpt-4o-mini', api_key=api_key)
    dspy.configure(lm=lm)

    # each function has 5 candidates
    n = 5

    # Example requirements text
    requirements_text = (
        "Develop a modular calculator that supports addition, subtraction, multiplication, and division. "
        "The system should be divided into smaller functions to handle basic operations independently, "
        "and a main function to integrate these operations."
    )

    # Architect agent
    test_architect_agent = ArchitectAgent(llm=lm,
                                           analysis_prompt_template=prompt.analysis_prompt_template,
                                            generation_prompt_template=prompt.generation_prompt_template)
    
    
    analysis_text, auxiliary_function_interfaces, main_function_interfaces = test_architect_agent.architect(requirements_text)

    # Developer agent
    test_developer_agent = DeveloperAgent(llm=lm,
                                          task_description=prompt.developer_agent_prompt,
                                          n=n)
    
    auxiliary_functions = []
    for auxiliary_function_interface in auxiliary_function_interfaces:
        candidates = test_developer_agent.generate_candidates(auxiliary_function_interface, analysis_text, 2)
        auxiliary_functions.append(candidates)
    
    # print
    print("——————————————————————————————————————————————————————————————————————————————————————————————")
    for candidates in auxiliary_functions:
        print(candidates[0])