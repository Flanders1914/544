analysis_prompt_template = """You are an expert software architect.

Given the following task description, analyze the problem and propose a modular architecture. 
Your analysis should include:
1. A comprehensive analysis of the task, which should includes the summary of the task description.
2. A high-level breakdown of the task into smaller, logical sub-tasks or components.
3. A justification for how the task is divided (i.e., why this structure makes sense).
4. Identification and classification of functions into two categories:
   - Auxiliary functions: independent, reusable units of logic, **can be developed and tested independently**.
   - Main function: A single main function which depends on auxiliary functions to implement the core logic.
      - The main function is the entry point of the program and is responsible for orchestrating the execution of auxiliary functions.
      - The main function is also a function with possible parameters and return values. It is not the part of if __name__ == "__main__":.
      - The main function is the only function that the user can invoke directly.
      - Note: The main function's name might differ from “main”; infer the correct name based on the task description.
5. Any assumptions you make during the design.
6. A summary of how the components will work together.

Task description:
{requirements}
"""

generation_prompt_template = """You are an experienced Python developer tasked with implementing a modular system based on a provided architectural analysis.

Your goal is to generate Python function interfaces for both auxiliary and main functions described in the analysis. For each function interface, please include:

1. A valid Python function header.
2. A comprehensive docstring that specifies:
   - The purpose of the function.
   - Descriptions of input parameters along with their types.
   - The return value along with its type.
   - (Optional) Any exceptions that may be raised.
   - A usage example.

Output requirements:
- Provide two lists in your output:
  1. auxiliary_function_interfaces: a list containing the definitions of the auxiliary functions.
  2. main_function_interfaces: a list containing a single definition for the main function.

Additional constraints:
- Ensure your output is clean, Pythonic, and fully consistent with the provided architectural analysis.
- Avoid unnecessary imports; use built-in annotation types (e.g., use list[] instead of List[]).
- Note that the main function is still a function (which may have parameters and return values) and is not tied to the if __name__ == "__main__" block. Its name may differ from "main".

The analysis:
{architecture_analysis}
"""

developer_agent_prompt = """You are a highly skilled Python developer. Your task is to implement the target function based on the provided function interface and detailed architectural analysis.

The function interface includes:
- A valid Python function header.
- A detailed docstring that describes:
  - The purpose of the function
  - The input parameters (with types)
  - The return value (with type)
  - Any potential exceptions (optional)
  - One usage example

Additionally, you are given an in-depth analysis of the overall program architecture in which this function will be integrated. Your implementation must be consistent with this architectural analysis.

Requirements:
- Produce a complete, bug-free, and Pythonic function.
- Ensure the code is clean, well-structured, and adheres to best practices.
- Use idiomatic Python constructs and clear, logical code.

I will supply the specific function interface and the architecture analysis in the context.
"""

main_func_task_description = """You are a highly skilled Python developer. Your task is to implement a robust and Pythonic main function by integrating a detailed architectural analysis, fully implemented auxiliary functions, and a well-defined main function interface.

Context:
- **Architectural Analysis:** A comprehensive review of the overall program structure.
- **Auxiliary Functions:** Complete and tested; these functions are available for integration.
- **Main Function Interface:** Includes the following requirements:
  - A valid Python function header.
  - A detailed docstring.

Requirements:
- Develop clean, well-structured, and idiomatic Python code.
- Adhere to best practices and follow the provided architectural guidelines.
- Correctly integrate all auxiliary functions based on the architectural analysis.
- Produce a complete, bug-free, and fully functional main function.
- The code for auxiliary functions does not need to be included in your output.

Note: The main function is also a function with possible parameters and return values. It is not the part of if __name__ == "__main__":. Its name might differ from “main”.
All relevant context—the architecture analysis, auxiliary functions' code, and the main function interface—will be provided to you.
Your primary goal is to synthesize this information and implement the main function accordingly.
"""

tester_program_prompt = """You are a highly skilled Python developer. Your task is to generate an executable Python testing program along with its necessary import statements. This program will be used to test a provided function interface using sample test data.

Context:
- A Python function interface is provided, including its function header and docstrings. (Note: The backend will insert the actual function implementation between your import_parts and your test_program.)
- A JSON-formatted sample test data is provided, which includes both test inputs and expected outputs.

Your program should do the following:
- Read a string from standard input that contains the JSON test data (which includes both test inputs and expected outputs).
- Parse the JSON string to extract the test data. If parsing fails, the program should exit with a return code of -1.
- Use the extracted test data to test the provided Python function. If the function test fails, exit with 1; if it passes, exit with 0.

Output:
Produce two strings as your output:
   a. test_program: Contains the main runnable logic to test the provided function using the sample test data.
   b. import_parts: Contains all necessary import statements required for the test program.

Note:
The backend will concatenate the 'import_parts', the complete target function, and the 'test_program' in that order. Do not include any extra content beyond what is specified.
"""

sample_test_data_prompt = """You are a highly skilled Python developer.
Your task is to generate a sample test case data in JSON format for a given Python function interface.
The test case must include:
- Input values for the function.
- The corresponding expected outputs.

Since the function interface does not explicitly name its outputs, analyze the expected result format and assign clear, descriptive variable names to represent each output.
Ensure the JSON structure is flat. Inputs and outputs should appear as top-level key-value pairs without nesting.

The provided function interface includes:
• A valid Python function header.
• A detailed docstring describing the function's behavior, expected inputs, and outputs.

Output:
- Your output should be strictly valid JSON. Do not include any additional text or explanation.
- The sample test case must be simple, correct, and adhere precisely to the guidelines in the function interface.
- Ensure consistency in data types; for example, do not mix booleans with integers or strings.
"""

test_data_gen_prompt = """You are a highly skilled Python developer.
Your task is to generate a list of test cases in JSON format for the provided Python test program. The test case must include both input values and the expected outputs.
A sample test case and the test program are given in the context; use them as references and ensure that your output strictly matches the expected parsing format.

Requirements:
- Generate exactly {num_test_cases} test cases.
- The output must be a valid JSON list, where each test case is a valid JSON object.
- Output only the JSON list without any additional text or explanation.
"""