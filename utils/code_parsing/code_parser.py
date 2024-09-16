import re
from typing import List, Tuple

def parse_input_original(response: str) -> Tuple[List[str], str, str]:
    """
    Original parse function.
    Parse the input response to extract requirements, code, and example.
    
    Args:
        response (str): Raw response from the model.
    
    Returns:
        Tuple[List[str], str, str]: A tuple containing requirements, code, and example.
    """
    requirements = []
    code = ""
    example = ""
    
    if "### Answer" in response or "### Corrected Code" in response:
        return ["none"], response, ""
    
    lines = response.strip().splitlines()
    current_section = None
    
    for line in lines:
        if line.startswith("### "):
            current_section = line[4:].lower()
        elif current_section == "requirements":
            if line.strip() and line.strip() not in ["bash", "```"]:
                requirement = line.strip("`").strip().lower()
                requirements.append(requirement)
        elif current_section in ["code", "example"]:
            if line.strip() not in ["```", "```python"]:
                if current_section == "code":
                    code += line + "\n"
                elif current_section == "example" and "import" not in line.strip():
                    example += line + "\n"
    
    return requirements, code.strip(), example.strip()