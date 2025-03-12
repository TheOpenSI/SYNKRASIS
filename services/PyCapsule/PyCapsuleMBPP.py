# ===================================================================================================
# DO NOT RUN, FOR EXAMPLE ONLY.
# ===================================================================================================
# PyCapsule for MBPP.
# Using default parser: utils.code_parsing.code_parser - parse_response
#
# Support functions - 
# - _create_test_function: Since MBPP has a list of test cases, 
#       we need to create a test function with all test cases.
# ===================================================================================================

# import os
# import sys
# sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

# from subprocess import CompletedProcess

# from services.PyCapsule.PyCapsuleBase import PyCapsuleBase
# from services.Container.Container import Container
# from services.LLM.LLMBase import LLMBase
# from modules.ExampleCallDetection import ExampleCallDetection
# from utils.code_parsing.code_parser import parse_response
# from utils.output_message_format.output_colour import print_pycapsule, print_error, print_warning

# class PyCapsuleMBPP(PyCapsuleBase):
#     def __init__(self, 
#                  container: Container, 
#                  llm: LLMBase,
#                  maximum_attempts: int = 9):
#         super().__init__(pycapsule_container=container, 
#                          llm = llm, 
#                          maximum_attempts=maximum_attempts)
    
    
#     def _set_prompt_paths(self):
#         self.helper_set_prompt_paths()
        
        
#     def _create_main_py(self, code, test_cases = "", meta_data = None) -> None:
#         if meta_data is None:
#             print_error("Meta data is required for MBPP, pass the problem dictionary as metadata")
#             raise ValueError("Meta data is required for MBPP, pass the problem dictionary as metadata")
        
#         if test_cases:
#             print_warning("Test cases are not required for MBPP, ignoring the test cases")
        
#         test_function: str = self._create_test_function(meta_data["test_list"])
#         time_safe_thread = self.timeout_code(function_name="test_function", 
#                                              args_for_function="()",
#                                              timeout=self.timeout)
#         sanitised_code = self.example_call_detection.extract_code_blocks(code)
#         py_file_content = (self.suppress_warning_code() +
#                            "\n\n" +
#                            sanitised_code +
#                            "\n\n" +
#                            test_function +
#                            "\n\n" +
#                            time_safe_thread)
        
#         main_py_path = os.path.join(self.MOUNT_DIR, "main.py")
#         task_file_path = os.path.join(self.MOUNT_DIR, f"task_{meta_data['task_id']}.py")
        
#         for file_path in [main_py_path, task_file_path]:
#             self.create_py_file(path=file_path,
#                                 content=py_file_content)
            
            
#     def _generate_code(self, user_query, 
#                        suppress_conversation_history = True) -> None:
#         # For MBPP, user query must be a dictionary which will be used as metadata.
#         if type(user_query) != dict:
#             print_error(("Failed to generate LLM response. "
#                          "User query must be a dictionary for MBPP"))
#             raise ValueError("User query must be a dictionary for MBPP")
        
#         llm_response: str = self.llm.generate_response(user_query["prompt"],
#                                                        None,
#                                                        suppress_conversation_history)
        
#         requirements, code = parse_response(llm_response)
#         self._create_main_py(code=code,meta_data=user_query)
#         self.create_requirements_txt(requirements)
        
        
#     def _get_fix_mode_query(self, response, meta_data):
#         # MBPP does not require any meta data for fix mode query.
#         return self.error_handling(error_message=response.stderr,
#                                    extract_test_case=True)     
    
    
#     def _update_code(self, fix_mode_query,
#                       suppress_conversation_history, 
#                       meta_data) -> None:
#         temp_data_point = meta_data.copy()
#         temp_data_point["prompt"] = fix_mode_query
#         self._generate_code(temp_data_point, suppress_conversation_history)
         
        
#     def _set_original_question(self, user_query: dict) -> str:
#         if type(user_query) != dict:
#             print_error(("Failed to set original question in the conversation histoy."
#                          "User query must be a dictionary for MBPP"))
#             raise ValueError("User query must be a dictionary for MBPP")
#         return user_query["prompt"]
    
    
#     def _call_fix_code(self, 
#                        response: CompletedProcess, 
#                        user_query: dict) -> tuple[int, int]:
#         if type(user_query) != dict:
#             print_error(("Failed to call fix code. "
#                          "User query must be a dictionary for MBPP"))
#             raise ValueError("User query must be a dictionary for MBPP")
        
#         return self.fix_code(response, user_query)
    
    
#     def _create_test_function(self, test_list: list) -> str:
#         """
#         Create the test function using the test list.
#         Function name is test_function().

#         Args:
#             test_list (list): list of test cases from the dataset.

#         Returns:
#             str: test function with all test cases + call to the function.
#         """
#         all_tests =  "\t" + "\n\t".join(test_list)
#         test_function = ("def test_function():\n"
#                          f"{all_tests}\n"
#                          "\n")
        
#         return test_function  
        