# =============================================================================================
# PyCapsule for LiveCodeBench.
#
# Two stage evaluation, all inside the same budget of `maximum_attempts` fix attempts:
#   1. Public tests  - failures get a detailed error analysis (ErrorHandling).
#   2. Private tests - only run once the public tests pass. A failure only tells the LLM that a
#                      hidden test case failed, no test data or error details are shared.
#                      If a later fix breaks the public tests again, that is a stage 1 failure 
#                      with the detailed error again.
# Failing the public tests within the budget is a fail. Pass means the final code passed both.
# Whether/when the public and private tests were cleared is kept in self.last_task_details.
# =============================================================================================

import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import json
import re
from subprocess import CompletedProcess

from services.PyCapsule.PyCapsuleBase import PyCapsuleBase
from services.Container.Container import Container
from services.LLM.LLMBase import LLMBase
from data.DatasetBase import DatasetBase
from utils.code_parsing.code_parser import parse_response
from utils.output_message_format.output_colour import print_error, print_info, print_success, print_pycapsule
from services.PyCapsule.livecodebench_harness.LCBHarness import LCBHarness
from services.BPD.lcb_trace import LCBTracer

class PyCapsule_LiveCodeBench(PyCapsuleBase):
    REQUIRED_KEYS = ["task_id", "prompt", "entry_point", "public_test", "private_test", "starter_code", "test_type"]

    PRIVATE_FAIL_QUERY = (
        "Your solution passes the public tests but fails a hidden test, so its logic is probably wrong or "
        "incomplete for inputs the examples do not cover.\n"
        "Re-derive the approach from the problem statement instead of patching the examples, then check: "
        "minimum/maximum constraint values and tiny inputs, duplicates and ties, time complexity at the "
        "maximum input size, and the exact output format.\n"
        "Rewrite the whole solution."
    )

    def __init__(self,
                 pycapsule_container: Container,
                 llm: LLMBase,
                 maximum_attempts: int = 5,
                 timeout: int = 10,
                 response_log_dir: str = None,
                 trace_feedback: bool = False) -> None:
        """
        PyCapsule_LiveCodeBench constructor.

        Args:
            pycasule_container (Container): Container object.
            llm (LLMBase): LLM object.
            maximum_attempts (int, optional): Maximum attempts to fix the code, shared by the public
                and private test stage. Defaults to 5.
            timeout (int, optional): Timeout in seconds for each test case. Defaults to 10.
            response_log_dir (str, optional): If set, every LLM query/raw response is saved under
                response_log_dir/task_<id>/attempt_<n>_{query,response}.txt. Defaults to None.
            trace_feedback (bool, optional): Append a BPD execution trace of the code on the first failing
                public test to the public failure feedback. Never used for private tests, the trace would 
                reveal their input. Defaults to False.
        """
        super().__init__(pycapsule_container, llm, maximum_attempts, timeout = timeout)
        self.harness = LCBHarness()
        self.response_log_dir = response_log_dir
        self.tracer = LCBTracer(self.harness) if trace_feedback else None
        self.trace_log: list[dict] = []   # one entry per trace attached: task_id, test_index, chars
        self._last_code = ""
        self._generation_count = 0
        self._reset_task_details()


    def _reset_task_details(self) -> None:
        self.last_task_details = {
            "public_cleared": False,
            "public_cleared_attempt": None,   # 0 = initial generation, 1.. = fix attempts
            "private_cleared": False,
            "private_cleared_attempt": None,
            "private_failure_types": []       # category of the first failed private test, per attempt
        }


    def _set_prompt_paths(self):
        return self.helper_set_prompt_paths()


    def __call__(self, user_query: dict) -> tuple[int, int, list[str]]:
        """
        Generate code, run public then private tests, fix until both pass or attempts run out.

        Returns:
            Tuple: return code (0 only if the private tests passed), number of fix attempts made,
                and list of error types per fix attempt.
        """
        self._generation_count = 0
        self._reset_task_details()

        self.llm.init_chat_history(self._set_original_question(user_query))
        self._generate_code(user_query)

        response: CompletedProcess = self.container.start_container()
        self._record_outcome(response, attempt = 0)

        flag, fix_mode_attempts, error_trace = response.returncode, 0, []
        if response.returncode != 0:
            print_error("Generated code did not pass all tests. Starting pycapsule in fix mode.")
            flag, fix_mode_attempts, error_trace = self._call_fix_code(response, user_query)

        self.llm.clear_chat_history()

        return flag, fix_mode_attempts, error_trace


    def _record_outcome(self, response: CompletedProcess, attempt: int) -> None:
        """
        Keep track of when the public and private tests were cleared.
        """
        stage = self.harness.classify_response(response)
        details = self.last_task_details

        if stage in ("private_fail", "pass") and not details["public_cleared"]:
            details["public_cleared"] = True
            details["public_cleared_attempt"] = attempt
            print_success(f"Public tests cleared at attempt {attempt}.")

        if stage == "private_fail":
            failure_type = response.stderr.replace(self.harness.PRIVATE_FAILED_PREFIX, "").strip()
            details["private_failure_types"].append(failure_type)
            print_info(f"Private test failed at attempt {attempt}: {failure_type}")

        if stage == "pass":
            details["private_cleared"] = True
            details["private_cleared_attempt"] = attempt
            print_success(f"Private tests cleared at attempt {attempt}.")


    def _save_generation(self, user_query: dict, response: str) -> None:
        """
        Save the exact query sent to the LLM and its raw response, one pair per generation.
        Attempt 0 is the initial generation, 1.. are fix mode attempts.
        """
        if self.response_log_dir is None:
            return
        task_dir = os.path.join(self.response_log_dir, f"task_{user_query['task_id']}")
        self.create_py_file(os.path.join(task_dir, f"attempt_{self._generation_count}_query.txt"),
                            user_query["prompt"])
        self.create_py_file(os.path.join(task_dir, f"attempt_{self._generation_count}_response.txt"),
                            response or "")
        self._generation_count += 1


    def _generate_code(self, user_query: dict, suppress_conversation_history: bool = True) -> None:
        self.validate_metadata(dict, user_query, self.REQUIRED_KEYS)

        response = self.llm.generate_response(user_prompt = user_query["prompt"],
                                              suppress_conversation_history = suppress_conversation_history)
        self._save_generation(user_query, response)

        # https://support.leetcode.com/hc/en-us/articles/360011833974-What-are-the-environments-for-the-programming-languages
        code = self._extract_code(response) # no req, default env set

        self._create_main_py(code, user_query)


    def _extract_code(self, response: str) -> str:
        """
        parse_response, plus a fallback for a repeated code fence, e.g. "### Code\\n```\\n```python\\n...```"
        which parse_response reads as empty code.
        """
        _, code = parse_response(response)
        if code.strip():
            return code
        lines = response.split("### Code")[-1].split("\n")
        fences = [i for i, line in enumerate(lines) if re.match(r"^\s*```", line)]
        if len(fences) < 2:
            return ""
        body = [line for line in lines[fences[0] + 1:fences[-1]] if not re.match(r"^\s*```\w*\s*$", line)]
        return "\n".join(body).strip()


    def _create_main_py(self, code: str, user_query: dict) -> None:
        """
        main.py is the test driver, solution.py is the LLM code wrapped by the harness and
        private_tests.json holds the private tests (kept out of main.py, they can be large).
        The driver runs solution.py once per test case.
        """
        self._last_code = code
        solution_content = self.harness.build_solution_content(user_query, code)
        driver_content = (self.suppress_warning_code() + "\n\n" +
                          self.harness.build_driver_content(user_query["public_test"], self.timeout))
        private_tests = user_query["private_test"]
        if isinstance(private_tests, str):
            private_tests = json.loads(private_tests)

        # File path
        task_dir = os.path.join(self.MOUNT_DIR, f"task_{user_query['task_id']}")

        # main.py, solution.py and private_tests.json are what the container uses,
        # the task folder keeps a copy of the code for analysis.
        self.create_py_file(os.path.join(self.MOUNT_DIR, "main.py"), driver_content)
        self.create_py_file(os.path.join(self.MOUNT_DIR, self.harness.SOLUTION_FILE_NAME), solution_content)
        self.create_py_file(os.path.join(self.MOUNT_DIR, self.harness.PRIVATE_TESTS_FILE_NAME),
                            json.dumps(private_tests))
        self.create_py_file(os.path.join(task_dir, "llm_generated_code.py"), code)
        self.create_py_file(os.path.join(task_dir, self.harness.SOLUTION_FILE_NAME), solution_content)
        self.create_py_file(os.path.join(task_dir, "harness_code.py"), driver_content)


    def _get_fix_mode_query(self, response: CompletedProcess, meta_data: dict) -> str:
        """
        Private test failure -> generic query, nothing about the hidden tests is shared.
        Public test failure -> detailed error handling, also when the public tests had cleared before 
        (a regression), the public tests are the samples already in the prompt.
        """
        stage = self.harness.classify_response(response)

        if not self._last_code.strip():
            self._current_error_type = ["NoCodeFound"]
            return ("Your response did not contain any code. Put the complete solution in the '### Code' "
                    "section, inside a single pair of triple backticks.")

        if stage == "private_fail":
            self._current_error_type = ["PrivateTestFailed"]
            return self.PRIVATE_FAIL_QUERY

        if "Generated code is running infinite loop" in response.stderr:
            # On LiveCodeBench this is mostly an inefficient algorithm, not an infinite loop.
            self._current_error_type = ["TimeLimitExceeded"]
            failed_input = response.stderr.strip().split("\n")[0]
            return (f"Your generated code exceeded the time limit of {self.timeout} seconds on a public test case.\n"
                    f"{failed_input}\n"
                    "Your algorithm is probably too slow for the given constraints (or loops forever). "
                    "Please use a more efficient algorithm or data structures, and make sure all loops terminate.")

        query = self.error_handling(response.stderr)
        self._current_error_type = list(self.error_handling.current_error_type)
        return query + self._trace_section(meta_data)


    def _trace_section(self, user_query: dict) -> str:
        """
        BPD trace of the current code on the first failing public test, empty if not enabled or the code 
        cannot be traced.
        """
        if self.tracer is None:
            return ""
        traced = self.tracer.trace_first_failing_public_test(user_query, self._last_code)
        if traced is None:
            return ""
        self.trace_log.append({"task_id": user_query["task_id"], "test_index": traced["test_index"],
                               "chars": len(traced["report"])})
        return ("\n\nExecution trace of your code on public test case "
                f"{traced['test_index'] + 1}, recorded line by line like a debugger session:\n"
                f"{traced['report']}\n"
                "Find the first point where the behaviour differs from what the problem requires and fix that logic.")


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
        """
        Fix loop, replaces the base fix_code because the stage (public/private) decides the query
        and the outcome of every attempt must be recorded.
        """
        self.validate_metadata(dict, user_query, self.REQUIRED_KEYS)
        print_pycapsule("Starting PyCapsule in fix mode.")

        attempt_count = 0
        error_trace: list[str] = []

        while response.returncode != 0 and attempt_count < self.maximum_attempts:
            self._change_system_prompt(is_fix_mode = True)

            fix_mode_query = self._get_fix_mode_query(response, user_query)
            error_trace.append(self._current_error_type)

            self._update_code(fix_mode_query = fix_mode_query,
                              suppress_conversation_history = False,
                              meta_data = user_query)

            response = self.container.start_container()
            attempt_count += 1
            self._record_outcome(response, attempt_count)

        self._change_system_prompt()  # Resetting the system prompt to normal mode

        return response.returncode, attempt_count, error_trace


    def run_pycapsule_experiment(self, dataset: DatasetBase) -> None:
        """
        Same as the base class but also saves whether the public and private tests were cleared.
        The dataset must support the extra fields in append_result (LiveCodeBench does).
        """
        while True:
            data_point = dataset.get_next()
            if data_point is None:
                break

            solve_flag, fix_mode_attempt_count, error_trace = self.__call__(data_point)
            status = "pass" if solve_flag == 0 else "fail"
            if solve_flag == 0:
                dataset.solved_count += 1
            else:
                dataset.unsolved_count += 1

            dataset.append_result(
                task_id = data_point["task_id"],
                fix_mode_attempt_count = fix_mode_attempt_count,
                status = status,
                error_trace = error_trace,
                **self.last_task_details
            )
            dataset.log_to_csv()
            dataset.log_to_json()

            print("#" * 50)
            print(f"Solved {dataset.solved_count} problems, "
                  f"Unsolved {dataset.unsolved_count} problems")
            print("#" * 50)


    def cleanup(self):
        super().cleanup()
        for file in [self.harness.SOLUTION_FILE_NAME, self.harness.PRIVATE_TESTS_FILE_NAME]:
            file_path = os.path.join(self.MOUNT_DIR, file)
            if os.path.exists(file_path):
                os.remove(file_path)
