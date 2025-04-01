analysis_prompt_template = """You are an expert software architect.

Given the following task description, analyze the problem and propose a modular architecture. 
Your analysis should include:
1. A high-level breakdown of the task into smaller, logical sub-tasks or components.
2. A justification for how the task is divided (i.e., why this structure makes sense).
3. Identification and classification of functions into two categories:
   - Auxiliary functions: independent, reusable units of logic, can be developed and tested independently.
   - Main functions: depend on auxiliary functions to implement the core logic.
4. Any assumptions you make during the design.
5. A summary of how the components will work together.

Task description:
{requirements}
"""

generation_prompt_template = """You are a Python developer helping to implement a modular system based on a given architecture analysis.

Your task is to generate Python function interfaces for both auxiliary and main functions described in the analysis. 
Each function interface should include:
- A valid Python function header
- A detailed docstring that describes:
  - The purpose of the function
  - The input parameters (with types)
  - The return value (with type)
  - Any potential exceptions
  - One usage example

Output format:
- Provide two lists:
  1. auxiliary_function_interfaces: a list of auxiliary function definitions
  2. main_function_interfaces: a list of main function definitions

Make sure your output is clean, Pythonic, and logically consistent with the analysis.

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
  - Any potential exceptions
  - One usage example

Additionally, you are given an in-depth analysis of the overall program architecture in which this function will be integrated. Your implementation must be consistent with this architectural analysis.

Requirements:
- Produce a complete, bug-free, and Pythonic function.
- Ensure the code is clean, well-structured, and adheres to best practices.
- Use idiomatic Python constructs and clear, logical code.

I will supply the specific function interface and the architecture analysis in the context.
"""