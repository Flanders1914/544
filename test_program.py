import sys
import json
def is_palindrome(s: str, start: int, end: int) -> bool:
    """
    Checks if the substring from start to end is a palindrome.

    Parameters:
    s (str): The input string.
    start (int): The starting index of the substring.
    end (int): The ending index of the substring.

    Returns:
    bool: True if the substring is a palindrome, False otherwise.

    Example:
    >>> is_palindrome('racecar', 0, 6)
    True
    """
    while start < end:
        if s[start] != s[end]:
            return False
        start += 1
        end -= 1
    return True

def min_cut_dp(s: str) -> int:
    """
    Implements the dynamic programming approach to find the minimum cuts needed for palindrome partitioning.

    Parameters:
    s (str): The input string.

    Returns:
    int: The minimum number of cuts needed for a palindrome partitioning.

    Example:
    >>> min_cut_dp('aab')
    1
    """
    n = len(s)
    if n == 0:
        return 0

    # Create a DP array to store the minimum cuts needed for each substring
    dp = [0] * n
    # Create a 2D list to check if substrings are palindromic
    is_palindrome = [[False] * n for _ in range(n)]

    for end in range(n):
        min_cuts = end  # Maximum cuts needed is the length of the substring
        for start in range(end + 1):
            if s[start] == s[end] and (end - start <= 2 or is_palindrome[start + 1][end - 1]):
                is_palindrome[start][end] = True
                # If the whole substring is a palindrome, no cuts are needed
                min_cuts = 0 if start == 0 else min(min_cuts, dp[start - 1] + 1)
        dp[end] = min_cuts

    return dp[-1]


def min_palindrome_cuts(s: str) -> int:
    """
    Computes the minimum cuts needed to partition the string into palindromic substrings.

    Parameters:
    s (str): The input string.

    Returns:
    int: The minimum number of cuts needed for a palindrome partitioning.

    Example:
    >>> min_palindrome_cuts('ab')
    1
    """
    if not s:
        return 0
    return min_cut_dp(s)
def main():
    import json
    import sys

    # Read JSON input from standard input
    input_data = sys.stdin.read()

    # Parse the JSON data
    try:
        test_data = json.loads(input_data)
    except json.JSONDecodeError:
        sys.exit(-1)

    # Extract input and expected output
    test_input = test_data["input"]
    expected_output = test_data["expected_output"]

    # Call the function with the test input
    result = min_palindrome_cuts(test_input)

    # Check if the result matches the expected output
    if result == expected_output:
        sys.exit(0)  # Test passed
    else:
        sys.exit(1)  # Test failed

if __name__ == "__main__":
    main()