# architect_agent.py
import dspy

class ArchitectAnalysisSignature(dspy.Signature):
    task_description: str = dspy.InputField(desc="The description of your task.")
    architecture_analysis: str = dspy.OutputField(desc="Detailed analysis of the program architecture.")

class InterfaceGenerationSignature(dspy.Signature):
    task_description: str = dspy.InputField(desc="The description of your task.")
    generation_prompt: str = dspy.InputField(desc="Detailed analysis of your task and the program architecture.")
    auxiliary_function_interfaces: list[str] = dspy.OutputField(desc="The list of auxiliary function interfaces which includes the function header and docstring.")
    main_function_interfaces: list[str] = dspy.OutputField(desc="The list of main function interfaces which includes the function header and docstring.")

class ArchitectAgent(dspy.Module):
    """
     Architect Agent:
    1. Analyzes user requirements and produces an architecture analysis text.
       This analysis explains key design decisions and decomposes the overall task.
       The resulting analysis text can be shared with other agents to reinforce their understanding.
    2. Generates function interfaces based on the analysis text for both auxiliary and main functions.
        Each interface includes a function signature and detailed comments(docstrings) adhere to standard python conventions.
    """

    def __init__(self, llm, analysis_prompt_template, generation_prompt_template):
        """
        Initialize the Architect Agent with:
          - llm: An instance of the language model to be used.
          - analysis_prompt_template: Template to generate an analysis text from requirements.
          - generation_prompt_template: Template to generate function headers and docstrings based on the analysis.
        """
        self.llm = llm
        self.analysis_prompt_template = analysis_prompt_template
        self.generation_prompt_template = generation_prompt_template
        # Create Chain-of-Thought modules for each step
        self.analysis_cot = dspy.ChainOfThought(ArchitectAnalysisSignature)
        self.generate_cot = dspy.ChainOfThought(InterfaceGenerationSignature)
    
    def generate_architecture_analysis(self, user_requirements):
        """
        Generate a detailed analysis text from the given user requirements.
        """
        # Format the prompt with the given requirements
        prompt = self.analysis_prompt_template.format(requirements=user_requirements)
        # Use the LLM to generate the analysis text via dspy's Chain-of-Thought
        analysize = self.analysis_cot(task_description=prompt)
        architecture_analysis = analysize.architecture_analysis
        return architecture_analysis
    
    def generate_function_interfaces(self, task_description, architecture_analysis):
        """
        Generate function interfaces for both auxiliary and main functions with detailed comments.
        The interfaces are based on the architecture analysis text produced earlier.
        
        Parameters:
            architecture_analysis (str): The architecture analysis text.
        
        Returns:
            auxiliary_function_interfaces (list[str]): The generated list of auxiliary function interfaces
            main_function_interface (list[str]): The generated list of main function interfaces
        """
        # Generate the function interfaces using the LLM
        generation_prompt = self.generation_prompt_template.format(architecture_analysis=architecture_analysis)
        generate = self.generate_cot(task_description=task_description, generation_prompt=generation_prompt)
        auxiliary_function_interfaces = generate.auxiliary_function_interfaces
        main_function_interfaces =  generate.main_function_interfaces
        return  auxiliary_function_interfaces, main_function_interfaces
    
    def architect(self, requirements):
        """
        Main method to run the architecting process.
        Steps:
          1. Generate the architecture analysis text from requirements.
          2. Generate detailed function interfaces based on the analysis.
        
        Parameters:
            requirements (str): The user-provided requirements text.
        
        Returns:
            analysis_text (str): The generated analysis text.
            auxiliary_function_interfaces (list[str]): The generated list of auxiliary function interfaces
            main_function_interface (list[str]): The generated list of main function interfaces
        """
        # Step 1: Generate architecture analysis text
        print("Architect-agent: start analysis the architecture of the program")
        analysis_text = self.generate_architecture_analysis(requirements)
        print(f"Architect-agent: the result of the analysis:\n{analysis_text}")

        # Step 2: Generate function interfaces with detailed comments
        print("Architect-agent: start generate the function interfaces")
        auxiliary_function_interfaces, main_function_interfaces = self.generate_function_interfaces(requirements, analysis_text)
        print(f"Architect-agent: auxiliary function interfaces:\n{auxiliary_function_interfaces}")
        print(f"Architect-agent: main function interfaces:\n{main_function_interfaces}")
        return analysis_text, auxiliary_function_interfaces, main_function_interfaces


# Example usage (if run as a script)
if __name__ == "__main__":
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
    
    # Initialize a LLM instance
    api_key = "********"
    lm = dspy.LM('openai/gpt-4o-mini', api_key=api_key)
    dspy.configure(lm=lm)
    
    # Create the Architect Agent
    architect_agent = ArchitectAgent(
        llm=lm,
        analysis_prompt_template=analysis_prompt_template,
        generation_prompt_template=generation_prompt_template
    )
    
    # Example requirements text
    requirements_text = (
        "Develop a modular calculator that supports addition, subtraction, multiplication, and division. "
        "The system should be divided into smaller functions to handle basic operations independently, "
        "and a main function to integrate these operations."
    )

    architect_agent.architect(requirements_text)