import re
from typing import List, Tuple

def parse_codellama(response: str) -> Tuple[List[str], str, str]:
    """
    Parse the CodeLlama response to extract requirements, code, and example.
    
    Args:
        response (str): Raw response from the CodeLlama model.
    
    Returns:
        Tuple[List[str], str, str]: A tuple containing requirements, code, and example.
    """
    requirements = []
    code = ""
    example = ""
    
    # Split the response into sections based on ### markers or when no ### sections exist
    sections = re.split(r"###\s*", response)
    
    for section in sections:
        if not section.strip():
            continue
        
        parts = section.split("\n", 1)
        if len(parts) <= 1:
            continue
        
        section_name, content = parts[0].strip().lower(), parts[1].strip()
        
        # Handle the "requirements" section
        if section_name == "requirements":
            requirements = [req.strip() for req in content.split(" ")]
        
        # Handle the "code" and "example" sections
        elif section_name in ["code", "example"]:
            # Extract content between triple backticks for code or example sections
            code_match = re.search(r"```(?:python)?\s*([\s\S]*?)\s*```", content)
            if code_match:
                extracted_code = code_match.group(1).strip()
                if section_name == "code":
                    code = extracted_code
                else:
                    example = extracted_code

        # Handle the case where there are no specific sections but code and example are present
        else:
            # Look for any code blocks in the natural language section
            code_matches = re.findall(r"```(?:python)?\s*([\s\S]*?)\s*```", section)
            if code_matches:
                if len(code_matches) >= 1:
                    code = code_matches[0].strip()  # First block is considered code
                if len(code_matches) >= 2:
                    example = code_matches[1].strip()  # Second block is considered example

    return requirements, code, example
