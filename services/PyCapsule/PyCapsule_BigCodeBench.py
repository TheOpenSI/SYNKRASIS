# =============================================================================================
# PyCapsule for BigCodeBench.
# Using default parser: utils.code_parsing.code_parser - parse_response
# The unit tests are run one by one by the harness (services/PyCapsule/bigcodebench_harness/BCBHarness.py),
# in a persistent container that has the libraries of the tasks (see services/Container/prepare_bcb_container.py).
# Every failed test is shown to the LLM, a failed assertion (a wrong answer) can get a BPD trace.
# =============================================================================================

import json
import os
import sys

sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

from collections import Counter
from subprocess import CompletedProcess
from typing import Optional

from services.PyCapsule.PyCapsuleBase import PyCapsuleBase
from services.PyCapsule.bigcodebench_harness.BCBHarness import BCBHarness
from services.PyCapsule.FixQueryManager import FixQueryManager, Failure, WRONG_ANSWER, ERROR
from services.BPD.bpd import LEGEND
from services.Container.Container import Container
from services.LLM.LLMBase import LLMBase
from utils.code_parsing.code_parser import parse_response
from utils.output_message_format.output_colour import print_error, print_info


class PyCapsule_BigCodeBench(PyCapsuleBase):

    # The instruction when only errors (no failed assertion) are left.
    ERROR_TASK = ("Fix the error shown above. Change only what is needed and keep the rest of the code as it is. "
                  "Then give the complete corrected code.")
    WRONG_ANSWER_TASK = ("Do not start over. Your code ran but failed an assertion of the unit test(s). Compare what your "
                         "code returned with what the assertion expects, find the part of your code that causes the "
                         "difference, say in one sentence what it should do instead, and change only what is needed to "
                         "fix it. Keep the rest of the code as it is. Then give the complete corrected code.")
    NO_CODE_MESSAGE = ("Your last reply had no code. Give the complete solution in a '### Code' section, enclosed with "
                       "triple backticks.")
    ANSWER_INTRO = "Following is the unit tests that failed, with the assertion that failed:"
    ERROR_INTRO = "Following is the error message(s) of the failed unit test(s). Fix the code accordingly."

    def __init__(self,
                 pycapsule_container: Container,
                 llm: LLMBase,
                 maximum_attempts: int = 5,
                 per_test_timeout: int = 30,
                 total_timeout: int = 300,
                 enable_bpd: bool = False,
                 max_traces: Optional[int] = 1,
                 calls_log_path: Optional[str] = None) -> None:
        """
        PyCapsule for the BigCodeBench dataset.

        Args:
            pycapsule_container (Container): Container object, it needs the libraries of the tasks.
            llm (LLMBase): LLM object.
            maximum_attempts (int, optional): Maximum attempts to fix the code. Defaults to 5.
            per_test_timeout (int, optional): Timeout in seconds for each unit test. Defaults to 30.
            total_timeout (int, optional): Timeout in seconds for all the unit tests of a task together, counted from
                when the code is loaded. Defaults to 300, the limit of the original BigCodeBench runs.
            enable_bpd (bool, optional): Add a BPD execution trace to the fix mode query for a failed assertion.
                The trace is made in the container. Defaults to False.
            max_traces (int, optional): At most this many traces in one fix mode query, the first failed assertions.
                None = a trace for every failed assertion. Defaults to 1.
            calls_log_path (str, optional): If given, one json line per attempt is appended to this file: task_id,
                attempt, prompt (the fix query with its traces), response, test_results (the result of every test,
                "pass" or the error). Defaults to None.
        """
        super().__init__(pycapsule_container, llm, maximum_attempts)
        self.per_test_timeout = per_test_timeout
        self.total_timeout = total_timeout
        self.harness = BCBHarness()
        self.max_traces = max_traces if enable_bpd else 0       # 0 = the container makes no trace
        self.calls_log_path = calls_log_path
        self.fix_query = FixQueryManager(legend = LEGEND,
                                         task = self.ERROR_TASK,
                                         wrong_answer_task = self.WRONG_ANSWER_TASK,
                                         answer_intro = self.ANSWER_INTRO,
                                         error_intro = self.ERROR_INTRO)
        self._last_code = ""                # code of the latest LLM response that had code
        self._no_code = False               # the latest LLM response had no code
        self._fixing = False                # the latest LLM call is a fix attempt
        self._pending_call = None           # the latest LLM call, written when its container run is back
        self._reset_task_details()


    def _set_prompt_paths(self) -> None:
        """
        Both system prompts are the ones of BigCodeBench: the generation prompt as it was before the
        LiveCodeBench change (no test cases), the fix prompt with tagged sections, change only what is needed.
        """
        prompts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts/bigcodebench")
        self.CODE_GEN_PROMPT_PATH = os.path.join(prompts_dir, "code_gen_prompt.txt")
        self.CODE_FIX_PROMPT_PATH = os.path.join(prompts_dir, "code_fix_prompt.txt")


    def _get_original_question(self, user_query: dict) -> str:
        return user_query["prompt"]


    def _create_main_py(self, code: str, user_query: dict) -> None:
        """
        Write the files into the mount directory, see BCBHarness for what they are.

        Args:
            code (str): Code extracted from the LLM response.
            user_query (dict): Original user query dictionary.
        """
        solution_content = self.harness.build_solution_content(code)
        candidate_content = self.harness.build_candidate_content(solution_content, user_query["test"])

        self.create_file(os.path.join(self.MOUNT_DIR, "solution.py"), solution_content)
        self.create_file(os.path.join(self.MOUNT_DIR, "tests.py"), user_query["test"])
        self.create_file(os.path.join(self.MOUNT_DIR, "candidate.py"), candidate_content)
        self.create_file(os.path.join(self.MOUNT_DIR, "main.py"),
                         self.harness.build_driver_content(user_query["test"], self.per_test_timeout, self.max_traces,
                                                           self.total_timeout))
        self.harness.copy_support_files(self.MOUNT_DIR)

        # a copy that stays after cleanup (the latest attempt of the task)
        self.create_file(os.path.join(self.MOUNT_DIR, f"bcb_task_{user_query['task_id']}.py"), candidate_content)


    def _generate_code(self,
                       user_query: dict,
                       suppress_conversation_history: bool = True) -> None:
        """
        Ask the LLM, extract the code from its response and write the files for the container.
        """
        self.validate_metadata(dict, user_query, ["task_id", "prompt", "entry_point", "test"])

        llm_response = self.llm.generate_response(user_prompt = user_query["prompt"],
                                                  suppress_conversation_history = suppress_conversation_history)

        # The libraries are in the container. parse_response raises on an empty response.
        try:
            _, code = parse_response(llm_response) if llm_response else ([], "")
        except Exception:
            code = ""

        if not self._fixing:
            self._last_code = ""           # a new task
        self._no_code = not code.strip()
        if self._no_code:
            # A failed attempt, not a crash: the fix query tells the LLM that its reply had no code.
            print_error(f"No code found in the response of the LLM for task {user_query['task_id']}.")
            code = self._last_code if self._fixing else ""      # run the previous code again (nothing on the first reply)
        else:
            self._last_code = code

        self._pending_call = {"task_id": user_query["task_id"], "prompt": user_query["prompt"], "response": llm_response}
        self._create_main_py(code, user_query)


    def _get_fix_mode_query(self, response: CompletedProcess, meta_data: dict) -> str:
        """
        The chat history is never sent (see _call_fix_code), the query has the problem, what failed and the code,
        see FixQueryManager. Every failed test is listed, a failed assertion (a wrong answer) with its trace
        if the container made one, an error with its concise message.
        The error types go to self.error_handling.current_error_type, fix_code stores them.
        """
        if self._no_code:
            self.error_handling.current_error_type = ["NoCode"]
            return self.fix_query.build(meta_data["prompt"], self._last_code,
                                        "Your last reply had no code.",
                                        [Failure(1, ERROR, self.NO_CODE_MESSAGE)])

        results = self.harness.parse_test_results(response.stderr)
        if results is None:
            print_error(f"The driver did not print the test results (exit code {response.returncode}).")
            raise RuntimeError(
                f"The driver did not print the test results for task {meta_data['task_id']} "
                f"(exit code {response.returncode}).\n"
                f"stderr:\n{response.stderr}\nstdout:\n{response.stdout}"
            )

        traces = self.harness.parse_traces(response.stderr)
        messages, error_types = self.harness.concise_results(results)
        self.error_handling.current_error_type = error_types
        failed_count = sum(result != self.harness.PASS for result in results)
        print_info(f"{failed_count} of {len(results)} tests failed: {dict(Counter(error_types))}")
        if traces:
            print_info(f"Added {len(traces)} execution trace(s) to the fix mode query.")

        failures = []
        for index, (result, message) in enumerate(zip(results, messages)):
            if result == self.harness.PASS:
                continue
            if self.harness.is_wrong_answer(result):
                failures.append(Failure(index + 1, WRONG_ANSWER, result.removeprefix("FAIL: "), trace = traces.get(index)))
            else:
                failures.append(Failure(index + 1, ERROR, message))

        summary = (f"Your previous solution failed {failed_count} of {len(results)} tests "
                   f"({', '.join(dict.fromkeys(error_types))}).")
        return self.fix_query.build(meta_data["prompt"], self._last_code, summary, self._group_errors(failures))


    def _group_errors(self, failures: list[Failure]) -> list[Failure]:
        """
        The same error message of several tests (e.g. an import error fails every test) is listed once,
        for the numbers of all these tests.
        """
        grouped, numbers = [], {}
        for failure in failures:
            if failure.kind == ERROR and failure.message in numbers:
                numbers[failure.message].append(failure.test)
            else:
                grouped.append(failure)
                if failure.kind == ERROR:
                    numbers[failure.message] = [failure.test]
        for failure in grouped:
            if failure.kind == ERROR and len(numbers[failure.message]) > 1:
                failure.test = ", ".join(str(number) for number in numbers[failure.message])
        return grouped


    def _update_code(self, fix_mode_query: str, suppress_conversation_history: bool, meta_data: dict) -> None:
        data_point = meta_data.copy()
        data_point["prompt"] = fix_mode_query
        self._fixing = True
        try:
            self._generate_code(data_point, suppress_conversation_history)
        finally:
            self._fixing = False


    def _call_fix_code(self, response: CompletedProcess, user_query: dict) -> tuple[int, int, list[str]]:
        # The history is always suppressed: every fix query has the problem, the previous code and the failures
        # in tagged sections, with the history the code and the problem would be sent twice.
        return self.fix_code(response, user_query, suppress_flag = True)


    def _reset_task_details(self) -> None:
        """
        Start the record of a task, saved with its result (see _get_result_details):
        tests_passed (list[str]): how many tests passed at every attempt, e.g. ["2/5", "5/5"].
        """
        self.task_details = {"tests_passed": []}


    def _on_container_response(self, response: CompletedProcess, attempt: int) -> None:
        """
        Called for every container run of a task.

        Args:
            response (CompletedProcess): Response from the container.
            attempt (int): 0 for the initial generation, 1.. for the fix attempts.
        """
        if attempt == 0:        # the first run of a new task
            self._reset_task_details()

        results = self.harness.parse_test_results(response.stderr)
        self._log_attempt(attempt, results)
        if results is not None:
            passed = sum(result == self.harness.PASS for result in results)
            self.task_details["tests_passed"].append(f"{passed}/{len(results)}")
            print_info(f"Attempt {attempt}: {passed} of {len(results)} tests passed.")


    def _log_attempt(self, attempt: int, results: Optional[list[str]]) -> None:
        """
        Append the latest LLM call with the result of its tests to calls_log_path (one json line).
        """
        if self.calls_log_path is not None and self._pending_call is not None:
            os.makedirs(os.path.dirname(os.path.abspath(self.calls_log_path)), exist_ok = True)
            with open(self.calls_log_path, "a") as log_file:
                log_file.write(json.dumps({**self._pending_call, "attempt": attempt, "test_results": results}) + "\n")
        self._pending_call = None


    def _get_result_details(self) -> dict:
        return self.task_details


    def cleanup(self):
        super().cleanup()
        for file in ["solution.py", "tests.py", "candidate.py", "results.jsonl"]:
            file_path = os.path.join(self.MOUNT_DIR, file)
            if os.path.exists(file_path):
                os.remove(file_path)
