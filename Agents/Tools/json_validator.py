import json
import re
from jsonschema import validate, ValidationError
from typing import Dict, Any, Tuple, List

REQUIREMENT_SCHEMA = {
    "type": "object",
    "required": ["project_info", "functional_requirements", "workflow_rules"],
    "properties": {
        "project_info": {
            "type": "object",
            "required": ["name", "description"],
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"}
            }
        },
        "functional_requirements": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "description"],
                "properties": {
                    "id": {"type": "string", "pattern": "^FR-[0-9]{3}$"},
                    "description": {"type": "string"},
                    "inputs": {"type": "array", "items": {"type": "string"}},
                    "outputs": {"type": "array", "items": {"type": "string"}},
                    "external_dependency": {"type": "string"}
                }
            }
        },
        "non_functional_requirements": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "description"],
                "properties": {
                    "id": {"type": "string", "pattern": "^NFR-[0-9]{3}$"},
                    "description": {"type": "string"}
                }
            }
        },
        "workflow_rules": {
            "type": "object",
            "required": ["critical_steps"],
            "properties": {
                "critical_steps": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "failure_scenarios": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["scenario", "expected_behaviour"],
                        "properties": {
                            "scenario": {"type": "string"},
                            "expected_behaviour": {"type": "string"}
                        }
                    }
                }
            }
        },
        "ambiguities": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["issue"],
                "properties": {
                    "requirement_id": {"type": "string"},
                    "issue": {"type": "string"}
                }
            }
        }
    }
}


def extract_json_from_markdown(text: str) -> str:
    """
    Extract JSON content from ```json ... ``` blocks.
    
    Args:
        text (str): The input text containing markdown.
        
    Returns:
        str: The extracted JSON string.
    """
    pattern = r'```json\s*([\s\S]*?)\s*```'
    matches = re.findall(pattern, text)
    
    if not matches:
        raise ValueError("No JSON code block found")
    
    if len(matches) > 1:
        raise ValueError(f"Multiple JSON code blocks found: {len(matches)}")
    
    return matches[0]


def fix_json_newlines(json_text: str) -> str:
    """
    Fix literal newlines inside JSON strings.
    Replaces newlines within quoted strings with spaces.
    
    Args:
        json_text (str): The JSON text to fix.
    
    Returns:
        str: The fixed JSON text.
    """
    result = []
    in_string = False
    escape_next = False
    
    for i, char in enumerate(json_text):
        if escape_next:
            result.append(char)
            escape_next = False
            continue
            
        if char == '\\':
            result.append(char)
            escape_next = True
            continue
            
        if char == '"':
            in_string = not in_string
            result.append(char)
            continue
            
        if char == '\n' and in_string:
            result.append(' ')
            continue
            
        result.append(char)
    
    return ''.join(result)


def validate_rq_analyst_agent_output(agent_response: str) -> Tuple[bool, List[str], Dict[Any, Any]]:
    """
    Validate requirement analysis agent output.
    
    Args:
        agent_response (str): The agent's response containing JSON.
    
    Returns:
        Tuple of (is_valid, errors, parsed_json)
    """
    errors = []
    
    try:
        json_text = extract_json_from_markdown(agent_response)
    except ValueError as e:
        return False, [str(e)], {}
    
    # Fix newlines in strings
    json_text = fix_json_newlines(json_text)
    
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON syntax: {str(e)}"], {}
    
    try:
        validate(instance=data, schema=REQUIREMENT_SCHEMA)
    except ValidationError as e:
        error_path = " -> ".join(str(p) for p in e.path) if e.path else "root"
        return False, [f"Schema validation failed at {error_path}: {e.message}"], {}
    
    # Additional validations
    warnings = []
    
    fr_ids = [req["id"] for req in data.get("functional_requirements", [])]
    duplicates = [id for id in set(fr_ids) if fr_ids.count(id) > 1]
    if duplicates:
        warnings.append(f"Duplicate FR IDs: {duplicates}")
    
    if "non_functional_requirements" in data:
        nfr_ids = [req["id"] for req in data["non_functional_requirements"]]
        duplicates = [id for id in set(nfr_ids) if nfr_ids.count(id) > 1]
        if duplicates:
            warnings.append(f"Duplicate NFR IDs: {duplicates}")
    
    fr_numbers = sorted([int(req["id"].split("-")[1]) for req in data.get("functional_requirements", [])])
    if fr_numbers and fr_numbers != list(range(1, len(fr_numbers) + 1)):
        warnings.append(f"FR IDs not sequential: {fr_numbers}")
    
    if "non_functional_requirements" in data:
        nfr_numbers = sorted([int(req["id"].split("-")[1]) for req in data["non_functional_requirements"]])
        if nfr_numbers and nfr_numbers != list(range(1, len(nfr_numbers) + 1)):
            warnings.append(f"NFR IDs not sequential: {nfr_numbers}")
    
    return True, warnings, data