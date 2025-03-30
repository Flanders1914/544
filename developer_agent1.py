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
    def __init__(self, llm, prompt_template, use_mock=False):
        self.llm = llm
        self.use_mock = use_mock#自测
        self.prompt_template = prompt_template
        # Initialize a chain-of-thought module for coding reasoning
        self.developer_cot = dspy.ChainOfThought(DeveloperSignature)

    def generate_candidates(self, function_interface, architecture_analysis="", num_candidates=3):
        """
        Generate multiple candidate implementations for a given function interface.
        Returns a list of candidate code implementations.
        """
        #自测
        if self.use_mock:
            return [
                f"def add(a, b):\n    return a + b  # candidate {i+1}"
                for i in range(num_candidates)
            ]
        
        candidates = []
        for _ in range(num_candidates):
            result = self.developer_cot(
                architecture_analysis=architecture_analysis,
                function_interface=function_interface
            )
            candidates.append(result.generate_function)
        return candidates

    
if __name__ == "__main__":
    # # TODO: test the developer agent
    # api_key = "*******"
    # lm = dspy.LM('openai/gpt-4o-mini', api_key=api_key)
    # dspy.configure(lm=lm)

    use_mock = True  # 自测

    if not use_mock:
        api_key = "*******"
        lm = dspy.LM("openai/gpt-4o-mini", api_key=api_key)
        dspy.configure(lm=lm)
    else:
        lm = None

    prompt_template = (
        "....."
    )

    agent = DeveloperAgent(
        llm=lm,
        prompt_template=prompt_template,
        use_mock=use_mock
    )

    if not use_mock:
        architecture = "..."
        func_interface = "..."
    else:
        # Mock inputs
        architecture = "A calculator system with modular functions."
        func_interface = "def add(a: float, b: float) -> float:\n    \"\"\"Returns the sum of two numbers.\"\"\""

    results = agent.generate_candidates(
        function_interface=func_interface,
        architecture_analysis=architecture,
        num_candidates=3
    )

    for i, code in enumerate(results, 1):
        print(f"\nCandidate #{i}:\n{code}")
