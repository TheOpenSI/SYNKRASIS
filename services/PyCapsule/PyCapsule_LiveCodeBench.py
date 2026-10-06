import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

from subprocess import CompletedProcess

from services.PyCapsule.PyCapsuleBase import PyCapsuleBase
from services.Container.Container import Container
from services.LLM.LLMBase import LLMBase
from utils.code_parsing.code_parser import parse_response
from services.PyCapsule.livecodebench_harness.LCBHarness import LCBHarness

class PyCapsule_LiveCodeBench(PyCapsuleBase):
    REQUIRED_KEYS = ["task_id", "prompt", "entry_point", "public_test", "private_test", "starter_code", "test_type"]

    def __init__(self,
                 pycapsule_container: Container,
                 llm: LLMBase,
                 maximum_attempts: int = 5,
                 timeout: int = 10) -> None:
        """
        PyCapsule_LiveCodeBench constructor.
        Only the public tests are used, both to drive the fix mode and to decide pass/fail.

        Args:
            pycasule_container (Container): Container object.
            llm (LLMBase): LLM object.
            maximum_attempts (int, optional): Maximum attempts to fix the code. Defaults to 5.
            timeout (int, optional): Timeout in seconds for each test case. Defaults to 10.
        """
        super().__init__(pycapsule_container, llm, maximum_attempts, timeout = timeout)
        self.harness = LCBHarness()


    def _set_prompt_paths(self):
        return self.helper_set_prompt_paths()


    def _generate_code(self, user_query: dict, suppress_conversation_history: bool = True) -> None:
        self.validate_metadata(dict, user_query, self.REQUIRED_KEYS)

        response = self.llm.generate_response(user_prompt = user_query["prompt"],
                                              suppress_conversation_history = suppress_conversation_history)

        # https://support.leetcode.com/hc/en-us/articles/360011833974-What-are-the-environments-for-the-programming-languages
        _, code = parse_response(response) # no req, default env set

        self._create_main_py(code, user_query)


    def _create_main_py(self, code: str, user_query: dict) -> None:
        """
        main.py is the test driver, solution.py is the LLM code wrapped by the harness.
        The driver runs solution.py once per public test case.
        """
        solution_content = self.harness.build_solution_content(user_query, code)
        driver_content = (self.suppress_warning_code() + "\n\n" +
                          self.harness.build_driver_content(user_query["public_test"], self.timeout))

        # File path
        task_dir = os.path.join(self.MOUNT_DIR, f"task_{user_query['task_id']}")

        # main.py and solution.py are what the container runs, the task folder keeps a copy for analysis.
        self.create_py_file(os.path.join(self.MOUNT_DIR, "main.py"), driver_content)
        self.create_py_file(os.path.join(self.MOUNT_DIR, self.harness.SOLUTION_FILE_NAME), solution_content)
        self.create_py_file(os.path.join(task_dir, "llm_generated_code.py"), code)
        self.create_py_file(os.path.join(task_dir, self.harness.SOLUTION_FILE_NAME), solution_content)
        self.create_py_file(os.path.join(task_dir, "harness_code.py"), driver_content)


    def _get_fix_mode_query(self, response: CompletedProcess, meta_data: dict) -> str:
        return self.error_handling(response.stderr)


    def _update_code(self,
                     fix_mode_query: str,
                     suppress_conversation_history: bool,
                     meta_data: dict) -> None:
        data_point = meta_data.copy()
        data_point["prompt"] = fix_mode_query
        self._generate_code(data_point, suppress_conversation_history)


    def _set_original_question(self, user_query: dict) -> str:
        return user_query["prompt"]


    def _call_fix_code(self,
                       response: CompletedProcess,
                       user_query: dict) -> tuple[int, int, list[str]]:
        self.validate_metadata(dict, user_query, self.REQUIRED_KEYS)

        return self.fix_code(response, user_query)


    def cleanup(self):
        super().cleanup()
        solution_path = os.path.join(self.MOUNT_DIR, self.harness.SOLUTION_FILE_NAME)
        if os.path.exists(solution_path):
            os.remove(solution_path)
