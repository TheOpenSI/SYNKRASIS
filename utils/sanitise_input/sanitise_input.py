# https://docs.python.org/3/library/shlex.html#shlex.quote

import re
import shlex

def sanitise_input(input_string: str) -> str:
    """
    Sanitizes input string by escaping special characters and validating it.
    Input string can only contain alphanumeric characters, '.', '_', ':', and '-'.

    Args:
        input_string (str): Input string to be sanitized.
        pattern (str): Regex pattern to validate the input.

    Raises:
        ValueError: If input string contains invalid characters.

    Returns:
        str: Sanitized input string.
    """
    pattern = r"^[a-zA-Z0-9._:-]+$"
    
    # Validate the input against the provided pattern
    if not re.match(pattern, input_string):
        raise ValueError(f"Invalid input: {input_string}")
    
    # Escape the input for safe shell usage
    return shlex.quote(input_string)



# if __name__ == "__main__":
#     print(sanitise_input("synkrasis"))
#     print(sanitise_input("synkrasis_alpha"))
#     print(sanitise_input("synk_mount"))
#     print(shlex.quote("start.sh"))
#     print(shlex.quote("start_rm_req.sh"))