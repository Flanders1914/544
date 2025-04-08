# main.py
from architect_agent import ArchitectAgent
from developer_agent import DeveloperAgent
from tester_agent import TesterAgent
import dspy
from dotenv import load_dotenv
import prompt
import os
from utils import Candidate, GeneratedFunction

def main():
    # Configure Language Model
    load_dotenv()
    api_key = os.environ.get('API_KEY')
    lm = dspy.LM('openai/gpt-4o-mini', api_key=api_key)
    dspy.configure(lm=lm)

    # Architect agent
    architect_agent = ArchitectAgent(llm=lm,
                                        analysis_prompt_template=prompt.analysis_prompt_template,
                                        generation_prompt_template=prompt.generation_prompt_template)
    
    # Developer agent
    developer_agent = DeveloperAgent(llm=lm,
                                        task_description=prompt.developer_agent_prompt,
                                        main_func_task_description=prompt.main_func_task_description,
                                        n=5)
    
    # Tester agent
    tester_agent = TesterAgent(llm=lm,
                                    tester_program_prompt=prompt.tester_program_prompt,
                                    sample_test_data_prompt=prompt.sample_test_data_prompt,
                                    test_data_gen_prompt=prompt.test_data_gen_prompt)
    
    requirements_text = (
        "Develop a modular calculator that supports addition, subtraction, multiplication, and division. "
        "The system should be divided into smaller functions to handle basic operations independently, "
        "and a main function to integrate these operations."
    )
    
    final_result = ""

    # Step 1: Architect agent
    generated_auxiliary_functions: list[GeneratedFunction] = None
    generated_main_functions: list[GeneratedFunction] = None

    analysis_text, generated_auxiliary_functions, generated_main_functions = architect_agent.architect(requirements_text)

    # Step 2: Developer agent develop auxiliary functions
    developer_agent.auxiliary_developer(generated_auxiliary_functions, analysis_text, error_threshold=2)

    # step 3: tester agent test auxiliary functions and choose the best one
    tester_agent.test_and_choose(generated_auxiliary_functions, 5)

    # Step 4: concatenate auxiliary functions
    for generated_auxiliary_function in generated_auxiliary_functions:
        final_result += generated_auxiliary_function.final_candidate.candidate_code + "\n\n"
    
    # Step 5: Developer agent develop the main function
    generated_main_function = generated_main_functions[0]
    generated_main_function.auxiliary_functions_code = final_result
    developer_agent.main_developer(generated_main_function, analysis_text, auxiliary_functions_code=final_result, error_threshold=2)

    # Step 6: tester agent test main function and choose the best one
    tester_agent.test_and_choose([generated_main_function], 5)

    # Step 7: print the final result
    final_result += generated_main_function.final_candidate.candidate_code
    print("_" * 100)
    print("Final Result:")
    print(final_result)

if __name__ == "__main__":
    main()

