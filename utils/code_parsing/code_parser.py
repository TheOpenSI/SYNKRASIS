'''
Structure of the code parser utility function
### Step-by-step reasoning
$reasoning

### Requirements
$external_libraries

### Code
'''

import re
from typing import List, Tuple

def parse_response(response: str) -> Tuple[List[str], str]:
    """
    Parse a structured response to extract requirements and code.

    Args:
        response (str): The structured response string to parse.

    Returns:
        - "requirements": List of required libraries (empty list if none)
        - "code": Extracted code as a string (empty string if not found)

    Raises:
        ValueError: If the response string is empty or not in the expected format.
    """
    if not response:
        raise ValueError("Empty response string provided")

    # Extract requirements
    requirements_match = re.search(r"### Requirements\s*(.*?)\s*###", response, re.DOTALL)
    if requirements_match:
        requirements_text = requirements_match.group(1).strip()
        if requirements_text.lower() == "none":
            requirements = []
        else:
            requirements = [req.strip() for req in requirements_text.split(",") if req.strip()]
    else:
        requirements = []

    # Extract code
    code_match = re.search(r"### Code\s*```(?:python)?(.*?)```", response, re.DOTALL)
    if code_match:
        code = code_match.group(1).strip()
    else:
        code = ""

    return requirements, code