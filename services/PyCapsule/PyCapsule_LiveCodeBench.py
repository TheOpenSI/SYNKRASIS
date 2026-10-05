import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import shutil

from subprocess import CompletedProcess

from services.PyCapsule.PyCapsuleBase import PyCapsuleBase
from services.Container.Container import Container
from services.LLM.LLMBase import LLMBase
from utils.code_parsing.code_parser import parse_response
from services.PyCapsule.livecodebench_harness.LCBHarness import LCBHarness
from utils.output_message_format.output_colour import print_info, print_pycapsule, print_warning

class PyCapsule_LiveCodeBench(PyCapsuleBase):
    def __init__(self,
                 pycapsule_container: Container,
                 llm: LLMBase,
                 maximum_attempts: int = 5) -> None:
        """
        PyCapsule_LiveCodeBench constructor.

        Args:
            pycasule_container (Container): Container object.
            llm (LLMBase): LLM object.
            maximum_attempts (int, optional): Maximum attempts to fix the code. Defaults to 5.
        """
        super().__init__(pycapsule_container, llm, maximum_attempts)
        self.harness = LCBHarness()


    def _set_prompt_paths(self):
        return self.helper_set_prompt_paths()


    def _generate_code(self, user_query, suppress_conversation_history = True) -> None:
        self.validate_metadata(
            dict, 
            user_query, 
            ["task_id", "prompt", "entry_point", "public_test", "private_test", "starter_code", "test_type"]
        )

        response = self.llm.generate_response(user_prompt = user_query["prompt"],
                                              suppress_conversation_history = suppress_conversation_history)

        # https://support.leetcode.com/hc/en-us/articles/360011833974-What-are-the-environments-for-the-programming-languages
        _, code = parse_response(response) # no req, default env set

        self._create_main_py(code, user_query)


    def _create_main_py(self, code: str, user_query: dict) -> None:
        test_type = user_query["test_type"]

        # Suppress warning
        suppress_warning = self.suppress_warning_code()

        # Test type based content generation
        harness_code = (self.harness.build_factorial_content(user_query, code) 
                        if test_type == "functional"
                        else self.harness.build_stdin_content(code))
                       
        py_file_content = suppress_warning + "\n\n" + harness_code

        # File path
        main_py_path = os.path.join(self.MOUNT_DIR, "main.py")
        llm_generated_code_path = os.path.join(self.MOUNT_DIR, f"task_{user_query['task_id']}", "llm_generated_code.py")
        harness_code_path = os.path.join(self.MOUNT_DIR, f"task_{user_query['task_id']}", "harness_code.py")

        # Generate files
        self.create_py_file(main_py_path, py_file_content)
        self.create_py_file(harness_code_path, py_file_content)
        self.create_py_file(llm_generated_code_path, code)