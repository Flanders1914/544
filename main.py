# main.py
from architect_agent import ArchitectAgent
from developer_agent import DeveloperAgent
from tester_agent import TesterAgent
import dspy
from dotenv import load_dotenv
import prompt
import os
from utils import Candidate, GeneratedFunction
from colorama import init, Fore, Style

def main():
    # Configure Language Model
    load_dotenv()
    api_key = os.environ.get('API_KEY')
    lm = dspy.LM('openai/gpt-4o-mini', api_key=api_key)
    dspy.configure(lm=lm)

    # Init colorama
    init()

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
    
    requirements_text = """
    Palindrome Partitioning II
    Given a string s, partition s such that every substring of the partition is a palindrome.
    Return the minimum cuts needed for a palindrome partitioning of s.
    Example 1:
    Input: s = \"aab\"
    Output: 1
    Explanation: The palindrome partitioning [\"aa\",\"b\"] could be produced using 1 cut.

    Example 2:
    Input: s = \"a\"
    Output: 0

    Example 3:
    Input: s = \"ab\"
    Output: 1

    Constraints:
    n1 <= s.length <= 2000
    s consists of lowercase English letters only.
    """
    
    final_result = ""

    # Step 1: Architect agent
    print(Fore.GREEN + Style.BRIGHT + "Step1: architect agent analysizes the architecture and designs interfaces" + Style.RESET_ALL)
    generated_auxiliary_functions: list[GeneratedFunction] = None
    generated_main_functions: list[GeneratedFunction] = None

    analysis_text, generated_auxiliary_functions, generated_main_functions = architect_agent.architect(requirements_text)

    # Step 2: Developer agent develop auxiliary functions
    print(Fore.GREEN + Style.BRIGHT + "Step 2: developer agent starts to develop auxiliary functions " + Style.RESET_ALL)
    developer_agent.auxiliary_developer(generated_auxiliary_functions, analysis_text, error_threshold=2)

    # step 3: tester agent test auxiliary functions and choose the best one
    print(Fore.GREEN + Style.BRIGHT + "Step 3: tester agent starts to test auxiliary functions and choose the final candidate " + Style.RESET_ALL)
    tester_agent.test_and_choose(generated_auxiliary_functions, 5)

    # Step 4: concatenate auxiliary functions
    print(Fore.GREEN + Style.BRIGHT + "Step 4: concatenate auxiliary functions" + Style.RESET_ALL)
    for generated_auxiliary_function in generated_auxiliary_functions:
        final_result += generated_auxiliary_function.final_candidate.candidate_code + "\n\n"
    
    # Step 5: Developer agent develop the main function
    print(Fore.GREEN + Style.BRIGHT + "Step 5: developer agent develops the main function" + Style.RESET_ALL)
    generated_main_function = generated_main_functions[0]
    generated_main_function.auxiliary_functions_code = final_result
    developer_agent.main_developer(generated_main_function, analysis_text, auxiliary_functions_code=final_result, error_threshold=2)

    # Step 6: tester agent test main function and choose the best one
    print(Fore.GREEN + Style.BRIGHT + "Step 6:  tester agent test main function and choose the best one" + Style.RESET_ALL)
    tester_agent.test_and_choose([generated_main_function], 5)

    # Step 7: print the final result
    final_result += generated_main_function.final_candidate.candidate_code
    print(Fore.GREEN + Style.BRIGHT + "\nFinal Result:(it is also saved in final_result.py)" + Style.RESET_ALL)
    print("_" * 100)
    print(final_result)
    # save the final result
    with open("final_result.py", "w") as f:
        f.write(final_result)


if __name__ == "__main__":
    main()

