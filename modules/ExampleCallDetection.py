# =====================================================================================================
# Example Call Detection Module
# Usage:
#     - extract_code_blocks(code: str) -> str:
#           Extracts specific code blocks from the code content.
#           Will remove anything that is not an instance of user defined tuple comprised
#           of types from ast, e.g. ast.Import, ast.ImportFrom, ast.FunctionDef.
# =====================================================================================================
import os
import sys 
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/..")

import ast
import astor
from deprecated import deprecated
from utils.output_message_format.output_colour import print_error


class ExampleCallDetection():

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

        idx = next(
            (
                i
                for i in range(len(content_body) - 1, -1, -1)
                if isinstance(content_body[i], ast.FunctionDef)
            ),
            None,  # if no FunctionDef exists
        )
        content_body = content_body[: idx + 1] if idx is not None else content_body
        
        return "\n".join([astor.to_source(item) for item in content_body])


    def remove_example_calls(self, code: str, class_name: str = "Solution") -> str:
        """
        Remove example calls from a class based solution (e.g. LeetCode style `class Solution`).
        extract_code_blocks only understands top level functions, it would keep example calls
        after a class and drop a class that follows a helper function.

        Keeps imports, function/class definitions and module level statements that do not
        touch the class under test. Drops `if __name__ == "__main__":` blocks, statements that
        reference class_name and statements that use a name assigned by a dropped statement,
        e.g. `sol = Solution()` followed by `print(sol.f(1))`.

        Args:
            code (str): The code to clean.
            class_name (str): Name of the class under test. Defaults to "Solution".

        Returns:
            str: Code without example calls, original code if it cannot be parsed.
        """
        try:
            body = ast.parse(code).body
        except Exception as e:
            print_error(f"Error parsing generated code. Returning original code. Error: {str(e)}")
            return code

        definitions = (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        dropped_names: set[str] = set()
        kept = []

        for item in body:
            if isinstance(item, definitions):
                kept.append(item)
                continue

            names = {n.id for n in ast.walk(item) if isinstance(n, ast.Name)}
            if self._is_main_guard(item) or class_name in names or names & dropped_names:
                dropped_names |= {n.id for n in ast.walk(item)
                                  if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
                continue
            kept.append(item)

        return "\n\n".join(ast.unparse(item) for item in kept)


    def _is_main_guard(self, node: ast.AST) -> bool:
        """
        Check if the node is an `if __name__ == "__main__":` block.
        """
        return (isinstance(node, ast.If)
                and isinstance(node.test, ast.Compare)
                and isinstance(node.test.left, ast.Name)
                and node.test.left.id == "__name__")


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
            # print_warning(f"Function {target_function_name} not defined in the code.")
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
        function_names = []
        for item in content_tree:
            if isinstance(item, ast.ImportFrom):
                for alias_object in item.names:  # list[alias_object]
                    function_names.append(alias_object.name)
        return function_names
 
 