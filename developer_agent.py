# developer_agent.py
import dspy

class DeveloperSignature(dspy.Signature):
    architecture_analysis: str = dspy.InputField(desc="Detailed analysis of the program architecture.")
    function_interface: str = dspy.InputField(desc="")
    generate_function: str = dspy.OutputField(desc="The complete function code based on the function interface.")

class DeveloperAgent(dspy.Module):
    """
    Developer Agent:
    - Receives function interfaces from the Architect Agent.
    - Generates multiple candidate implementations for each function.
    - Uses dspy's Chain-of-Thought to interact with the LLM for code generation.
    """
    def __init__(self, llm, prompt_template):
        self.llm = llm
        self.prompt_template = prompt_template
        # Initialize a chain-of-thought module for coding reasoning
        self.developer_cot = dspy.ChainOfThought(DeveloperSignature)

    def generate_candidates(self, function_interface):
        """
        Generate multiple candidate implementations for a given function interface.
        Returns a list of candidate code implementations.
        """
        # Format the prompt with the function interface details
        prompt = self.prompt_template.format(interface=function_interface)
        candidates = []
        # Generate multiple candidates (e.g., 3 candidates)
        for _ in range(3):
            response = self.cot_agent(prompt=prompt, config={"temperature": 0.8})
            candidates.append(response)
        return candidates
    
if __name__ == "__main__":
    # TODO: test the developer agent
    api_key = "*******"
    lm = dspy.LM('openai/gpt-4o-mini', api_key=api_key)
    dspy.configure(lm=lm)
