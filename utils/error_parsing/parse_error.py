from subprocess import CompletedProcess
import re

def parse_error_human_eval(response: CompletedProcess, data_point: dict, modify_assertion_error: bool = True) -> str:
    """
    FOR HUMANEVAL.
    Extracts error message from subprocess response and identifies specific error types.

    Args:
    - response (subprocess.CompletedProcess): The subprocess response.
    - data_point (dict): Contains information about the entry point.

    Returns:
    - str: Formatted error message.
    """

    # Filter error message and remove warningsf
    filtered_error_message = re.search(r"Traceback.*$", response.stderr, re.DOTALL)
    
    if filtered_error_message:
        error_response = filtered_error_message.group()
    else:
        error_response = response.stderr

    # Check for AssertionError
    if "AssertionError" in error_response:
        # Extract assertion error message
        assertion_error_match = re.search(r'assert (.*)\nAssertionError(.*)', error_response)
        if assertion_error_match:
            assertion_error_message = assertion_error_match.group(1)
            test_name = assertion_error_match.group(2)
            test_case = " " if test_name == "" else f" '{test_name}' "
            error_response = f"The following test case{test_case}failed and resulted in AssertionError.\nError message: {assertion_error_message}"
        else:
            error_response = f"An AssertionError occurred. Error message - \n{error_response}"

    # Check for SyntaxError
    elif "SyntaxError" in error_response:
        error_response = f"A SyntaxError occurred.\nError message: \n{error_response}"

    # Replace candidate with data_point["entry_point"]
    if modify_assertion_error:
        error_response = re.sub(r'candidate', data_point["entry_point"], error_response)
    
    return error_response


def parse_error_ds1000(response: CompletedProcess) -> str:
    """
    FOR DS1000.
    Extracts error message from subprocess response and identifies specific error types.
    
    Args:
    - response (subprocess.CompletedProcess): The subprocess response.
    
    Returns:
    - str: Formatted error message.
    """
    # Filter error message and remove warnings
    filtered_error_message = re.search(r"Traceback.*$", response.stderr, re.DOTALL)
    if filtered_error_message:
        error_response = filtered_error_message.group()
    else:
        error_response = response.stderr

    # Check for SyntaxError
    if "SyntaxError" in error_response:
        error_message = f"There was a syntax error. Error message is provided for reference:\n{error_response}"
    
    # Check for AssertionError
    elif "AssertionError" in error_response:
        error_message = (f"Your provided function logic failed a test case."
                         "Please re-evaluate the function and improve the function logic.\n{error_response}")
    
    # For other types of errors
    else:
        error_message = f"An error occurred. Error message:\n{error_response}"
    
    return error_message