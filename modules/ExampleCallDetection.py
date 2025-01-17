# =====================================================================================================
# Module for detecting example calls in the code.
# Usage:
#     - extract_code_blocks: Extracts specific code blocks from the code content.
#       Will remove anything that is not an instance of user defined tuple comprised
#       of types from ast, e.g. ast.Import, ast.ImportFrom, ast.FunctionDef.
# =====================================================================================================

import ast
import astor
from deprecated import deprecated
from utils.output_message_format.output_colour import print_error, print_warning, print_success


class ExampleCallDetection():
    def __init__(self,
                 to_keep: tuple[type] = (ast.Import, ast.ImportFrom, ast.FunctionDef)
                 ) -> None:
        """
        Parse the python content and extract code blocks based on the to_keep parameter.

        Args:
            to_keep (tuple[type], optional): The code blocks to keep e.g. Function, import etc.
            Defaults to None.
        """
        self.to_keep = to_keep


    def extract_code_blocks(self, code: str) -> str:
        """
        Extract specific code blocks according to self.to_keep from the code content.

        Args:
            code (str): The code to extract code blocks from.
            target_function_name (str): The name of the target function.
        
        Returns:
            extracted_code (str): The code blocks extracted.
            
        """
        try:
            content_tree = ast.parse(code)
            content_body = content_tree.body
            
        except Exception as e:
            print_error(f"Error parsing generated code. Returning original code. Error: {str(e)}")
            return code
        
        target = [item for item in content_body if isinstance(item, self.to_keep)]
        return "\n".join([astor.to_source(item) for item in target])


    def get_function_names(self, content_tree: list) -> list[str]:
        """
        Extracts all the DEFINED function names from the code content.
        Args:
            content_tree (list): List of ast nodes.

        Returns:
             Function_names (list[str]): List of function names.
        """
        function_names = []
        for item in content_tree:
            if isinstance(item, ast.FunctionDef):
                function_names.append(item.name)

        import_function_names = self._get_function_names_from_import(content_tree)
        return [item for sub_list in [function_names, import_function_names] for item in sub_list]


    @deprecated(version='0.0.1', reason="This function is under development, use with caution.")
    def does_contain_example_call(self, code: str, target_function_name: str) -> bool:
        """
        Check if the code contains example calls.

        Args:
            code (str): The code to check.
            target_function_name (str): The name of the target function.

        Returns:
            bool: True if the code is an example call, False otherwise.
        """
        content_tree: ast.Module = ast.parse(code)
        content_body: list = content_tree.body
        function_names = self.get_function_names(content_body)

        # Check if function exists in the code
        if target_function_name not in function_names:
            print_warning(f"Function {target_function_name} not defined in the code.")
            return False

        # Check if the function is called
        for item in content_body:
            # Function call
            if isinstance(item, (ast.Expr, ast.Assign)):
                if isinstance(item.value, ast.Call):
                    try:
                        if item.value.func.id == target_function_name:
                            return True
                    except AttributeError:
                        pass

        return False
    
    
    def _get_function_names_from_import(self, content_tree: list) -> list[str]:
        """
        Extracts all the IMPORTED function names from the import statement.
        Args:
            content_tree (list): List of ast nodes.

        Returns:
            Function_names (list[str]): List of function names.
        """
        to_keep = self.to_keep  # Just to get rid of warning on pycharm
        function_names = []
        for item in content_tree:
            if isinstance(item, ast.ImportFrom):
                for alias_object in item.names:  # list[alias_object]
                    function_names.append(alias_object.name)
        return function_names
