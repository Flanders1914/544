import sys
import json
def is_palindrome(substring: str) -> bool:
    """
    Checks if a given substring is a palindrome.

    Parameters:
    substring (str): The substring to check.

    Returns:
    bool: True if the substring is a palindrome, False otherwise.

    Example:
    >>> is_palindrome('aba')
    True
    >>> is_palindrome('abc')
    False
    """
    left, right = 0, len(substring) - 1
    while left < right:
        if substring[left] != substring[right]:
            return False
        left += 1
        right -= 1
    return True

def initialize_dp_table(length: int) -> list[int]:
    """
    Initializes the DP table for minimum cuts.

    Parameters:
    length (int): The length of the input string.

    Returns:
    list[int]: A list initialized to represent the minimum cuts needed for each substring.

    Example:
    >>> initialize_dp_table(3)
    [0, 0, 0]
    """
    return [0] * length


def min_cut_palindrome_partition(s: str) -> int:
    """
    Calculates the minimum cuts needed for a palindrome partitioning of the input string.

    Parameters:
    s (str): The input string to be partitioned.

    Returns:
    int: The minimum number of cuts needed for the palindrome partitioning.

    Example:
    >>> min_cut_palindrome_partition('aab')
    1
    >>> min_cut_palindrome_partition('a')
    0
    """
    if not s:
        return 0

    n = len(s)
    dp = initialize_dp_table(n)

    for i in range(n):
        min_cuts = i  # Maximum cuts possible
        for j in range(i + 1):
            if is_palindrome(s[j:i + 1]):
                min_cuts = 0 if j == 0 else min(min_cuts, dp[j - 1] + 1)
        dp[i] = min_cuts

    return dp[n - 1]
import sys
import json

def main():
    # Read JSON input from standard input
    input_data = sys.stdin.read()
    
    # Parse the JSON data
    try:
        test_data = json.loads(input_data)
    except json.JSONDecodeError:
        sys.exit(-1)
    
    # Extract input and expected output
    input_str = test_data["input"]
    expected_output = test_data["expected_output"]
    
    # Call the function to test
    actual_output = min_cut_palindrome_partition(input_str)
    
    # Check if the actual output matches the expected output
    if actual_output == expected_output:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()