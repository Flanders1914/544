import sys
import json
def min_cut_palindrome_partition(s: str) -> int:
    """
    Computes the minimum cuts needed for palindrome partitioning of the input string.

    Parameters:
    s (str): The input string to partition.

    Returns:
    int: The minimum number of cuts needed for palindrome partitioning.

    Example:
    >>> min_cut_palindrome_partition('aab')
    1
    >>> min_cut_palindrome_partition('a')
    0
    """
    n = len(s)
    if n == 0:
        return 0

    # Initialize the DP table
    dp = initialize_dp_table(n)
    
    for end in range(n):
        min_cuts = end  # Maximum cuts possible
        for start in range(end + 1):
            if is_palindrome(s[start:end + 1]):
                # If s[start:end + 1] is a palindrome, no cuts needed
                min_cuts = 0 if start == 0 else min(min_cuts, dp[start - 1] + 1)
        dp[end] = min_cuts

    return dp[n - 1]
import sys
import json

def main():
    # Read JSON input from standard input
    input_data = sys.stdin.read()
    
    try:
        # Parse the JSON data
        test_cases = json.loads(f'[{input_data}]')  # Wrap in brackets to form a valid JSON array
    except json.JSONDecodeError:
        sys.exit(-1)

    # Iterate through each test case
    for case in test_cases:
        input_str = case['input']
        expected_output = case['expected_output']
        
        # Call the function with the input string
        result = min_cut_palindrome_partition(input_str)
        
        # Check if the result matches the expected output
        if result != expected_output:
            sys.exit(1)  # Test failed

    sys.exit(0)  # All tests passed

if __name__ == "__main__":
    main()