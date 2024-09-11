import re

def parse_input_original(response: str):
    """
    Original parse function.
    Parse the input response to extract requirements, code, and example.
    Args:
        response (str): raw response from the model.
    """
    requirements = []
    code = ""
    example = ""
    if "### Answer" in response or "### Corrected Code" in response:
        return ["none"], response, ""
    
    lines = response.strip().splitlines()
    current_section = None
    for line in lines:
        if "### Requirements" in line:
            current_section = "requirements"
        elif "### Code" in line:
            current_section = "code"
        elif "### Example" in line:
            current_section = "example"
        else:
            if current_section == "requirements":
                if line.strip() not in ["bash", "```", ""]:
                    requirement = line.strip("`").strip().lower()
                    requirements.append(requirement)
            elif current_section == "code" or current_section == "example":
                if line.strip() not in ["```", "```python"]:
                    if current_section == "code":
                        code += line + "\n"
                    elif current_section == "example":
                        if "import" not in line.strip():
                            example += line + "\n"
    
    code = code.strip()
    example = example.strip()
    
    return requirements, code, example

def parse_input_improved(response: str):
    """
    Improved parse function.
    Parse the input response to extract requirements, code, and example.
    This function captures text between triple backticks for each section.
    Args:
        response (str): raw response from the model.
    """
    sections = {
        "Requirements": [],
        "Code": "",
        "Example": ""
    }
    
    # Use regex to find content between ### Section and the next ### or end of string
    section_pattern = r'### (\w+)(.*?)(?=### |\Z)'
    matches = re.finditer(section_pattern, response, re.DOTALL)
    
    for match in matches:
        section_name = match.group(1)
        content = match.group(2).strip()
        
        if section_name in sections:
            # Use regex to find content between triple backticks
            code_pattern = r'```(?:python)?\s*(.*?)\s*```'
            code_match = re.search(code_pattern, content, re.DOTALL)
            
            if code_match:
                if section_name == "Requirements":
                    # Split requirements into a list
                    sections[section_name] = [req.strip().lower() for req in code_match.group(1).split('\n') if req.strip()]
                else:
                    sections[section_name] = code_match.group(1).strip()
            elif section_name == "Requirements":
                # If no triple backticks, treat each line as a requirement
                sections[section_name] = [req.strip().lower() for req in content.split('\n') if req.strip()]
    
    return sections["Requirements"], sections["Code"], sections["Example"]