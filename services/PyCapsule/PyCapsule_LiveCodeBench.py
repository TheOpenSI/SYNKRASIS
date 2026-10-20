# =============================================================================================
# PyCapsule for LiveCodeBench.
# Using default parser: utils.code_parsing.code_parser - parse_response
# The tests are run by the harness (services/PyCapsule/livecodebench_harness/LCBHarness.py).
# =============================================================================================

import json
import os
import sys

sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

from collections import Counter
from subprocess import CompletedProcess
from typing import Optional

from services.PyCapsule.PyCapsuleBase import PyCapsuleBase
from services.PyCapsule.livecodebench_harness.LCBHarness import LCBHarness
from services.PyCapsule.FixQueryManager import FixQueryManager, Failure, WRONG_ANSWER, ERROR
from services.BPD.bpd import BPD, LEGEND
from services.Container.Container import Container
from services.LLM.LLMBase import LLMBase
from utils.code_parsing.code_parser import parse_response
from utils.output_message_format.output_colour import print_error, print_info, print_warning


class PyCapsule_LiveCodeBench(PyCapsuleBase):

    def __init__(self,
                 pycapsule_container: Container,
                 llm: LLMBase,
                 maximum_attempts: int = 5,
                 per_test_timeout: int = 10,
                 enable_bpd: bool = True,
                 max_traces: Optional[int] = 1,
                 calls_log_path: Optional[str] = None) -> None:
        """
        PyCapsule for the LiveCodeBench dataset.

        Args:
            pycapsule_container (Container): Container object.
            llm (LLMBase): LLM object.
            maximum_attempts (int, optional): Maximum attempts to fix the code. 
                Defaults to 5.
            per_test_timeout (int, optional): Timeout in seconds for each test case. 
                Defaults to 10.
            enable_bpd (bool, optional): Add a BPD execution trace to the fix mode 
                query for a public test with a wrong answer. Defaults to True.
            max_traces (int, optional): At most this many traces in one fix mode query, the first 
                wrong answers that can be traced. The other wrong answers are listed with their 
                input, expected and actual output. Every trace has the whole code, so more traces 
                mean much more text. None = no limit, every wrong answer gets a trace. Defaults to 1.
            calls_log_path (str, optional): If given, one json line per attempt is appended to this file:
                task_id, attempt, prompt (the fix query with its traces), response, test_results (the 
                result of every test, "pass" or the error). Defaults to None.
        """
        super().__init__(pycapsule_container, llm, maximum_attempts)
        self.per_test_timeout = per_test_timeout
        self.harness = LCBHarness()
        self.bpd = BPD() if enable_bpd else None 
        self.max_traces = max_traces
        self.calls_log_path = calls_log_path
        self._pending_call = None # the latest LLM call, written when its container run is back
        self.fix_query = FixQueryManager(legend = LEGEND)    # builds the fix mode queries
        self._last_code = "" # code of the latest LLM response
        self._number_of_public_tests = 0 # of the current task, the driver lists the public tests first
        self._reset_task_details()


    def _set_prompt_paths(self) -> None:
        """
        LiveCodeBench has its own system prompts.
        """
        prompt_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                  "prompts/livecodebench")
        self.CODE_GEN_PROMPT_PATH = os.path.join(prompt_dir, "code_gen_prompt.txt")
        self.CODE_FIX_PROMPT_PATH = os.path.join(prompt_dir, "code_fix_prompt.txt")


    def _get_original_question(self, user_query: dict) -> str:
        return user_query["prompt"]


    def _create_main_py(self, code: str, user_query: dict) -> None:
        """
        Write the files into the mount directory. The container uses the first three:
        - main.py: the driver, it runs solution.py once per test and prints the result 
            of every test.
        - solution.py: the code of the LLM, wrapped by the harness.
        - private_tests.json: the private tests.
        - lcb_task_<task_id>.py: a copy of latest solution.py that stays after cleanup.

        Args:
            code (str): Code extracted from the LLM response.
            user_query (dict): Original user query dictionary.
        """
        solution_content = self.harness.build_solution_content(user_query, code)

        # main
        self.create_file(
            os.path.join(self.MOUNT_DIR, "main.py"),
            self.harness.build_driver_content(
                user_query["public_test"],
                self.per_test_timeout,
            ),
        )

        # solution
        self.create_file(
            os.path.join(self.MOUNT_DIR, self.harness.SOLUTION_FILE_NAME), 
            solution_content
        )

        # private tests
        self.create_file(
            os.path.join(self.MOUNT_DIR, self.harness.PRIVATE_TESTS_FILE_NAME),
            user_query["private_test"]  # already a json string in the dataset
        )

        # task file
        self.create_file(
            os.path.join(self.MOUNT_DIR, f"lcb_task_{user_query['task_id']}.py"), 
            solution_content
        )


    def _generate_code(self, 
                       user_query: dict, 
                       suppress_conversation_history: bool = True) -> None:
        """
        Ask the LLM, extract the code from its response and write the files for the container.

        Args:
            user_query (dict): Original user query dictionary.
            suppress_conversation_history (bool, optional): Whether to suppress the conversation history.
                Defaults to True.
        """
        self.validate_metadata(dict, user_query, self._get_required_keys())

        llm_response = self.llm.generate_response(
            user_prompt = user_query["prompt"], 
            suppress_conversation_history = suppress_conversation_history
        )

        # The requirements are not installed. parse_response raises on an empty response.
        _, code = parse_response(llm_response) if llm_response else ([], "")

        if not code.strip():
            print_error(f"No code found in the response of the LLM for task {user_query['task_id']}.")
            raise ValueError(f"No code found in the response of the LLM for task {user_query['task_id']}. "
                             f"Check the response format against parse_response and the system prompt.\n"
                             f"Raw response:\n{llm_response}")

        self._number_of_public_tests = len(user_query["public_test"])
        self._pending_call = {"task_id": user_query["task_id"], "prompt": user_query["prompt"], "response": llm_response}
        self._store_last_generated_code(code)
        self._create_main_py(code, user_query)


    def _store_last_generated_code(self, code: str) -> None:
        """
        Store the last generated code for later use in fix mode queries.

        Args:
            code (str): The code generated by the LLM.
        """
        self._last_code = code


    def _reset_task_details(self) -> None:
        """
        Start the record of a task. Saved with the result of the task (see _get_result_details):
        - public_cleared / private_cleared (bool): did the code pass all public / all hidden tests at some attempt.
        - public_cleared_attempt / private_cleared_attempt (int): the first attempt that did. 
            0 is the initial generation, 1.. are the fix attempts. None if never.
        - private_failure_types (list[str]): one entry for every attempt that passed the public tests but failed 
            some hidden tests: the error types and how many hidden tests, e.g. "AssertionError=38, TimeoutError=2".
        """
        self.task_details = {
            "public_cleared": False,
            "public_cleared_attempt": None,
            "private_cleared": False,
            "private_cleared_attempt": None,
            "private_failure_types": []
        }


    def _on_container_response(self, response: CompletedProcess, attempt: int) -> None:
        """
        Called for every container run of a task. Keeps track of when the public and hidden tests were cleared.

        Args:
            response (CompletedProcess): Response from the container.
            attempt (int): 0 for the initial generation, 1.. for the fix attempts.
        """
        if attempt == 0:        # the first run of a new task
            self._reset_task_details()

        results = self.harness.parse_test_results(response.stderr)
        self._log_attempt(attempt, results)
        if results is None:     # the driver failed, _get_fix_mode_query raises about it
            return

        public_results = results[:self._number_of_public_tests]
        hidden_results = results[self._number_of_public_tests:]
        details = self.task_details

        if any(result != self.harness.PASS for result in public_results):
            return

        if not details["public_cleared"]:
            details["public_cleared"] = True
            details["public_cleared_attempt"] = attempt
            print_info(f"Public tests cleared at attempt {attempt}.")

        failed_count = sum(result != self.harness.PASS for result in hidden_results)
        if failed_count == 0:
            if not details["private_cleared"]:
                details["private_cleared"] = True
                details["private_cleared_attempt"] = attempt
                print_info(f"Hidden tests cleared at attempt {attempt}.")
        else:
            _, hidden_error_types = self.harness.concise_results(hidden_results)
            counts = ", ".join(f"{error_type}={count}" for error_type, count in Counter(hidden_error_types).items())
            details["private_failure_types"].append(counts)


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
        """
        Saved with the result of the task, the dataset takes these as keyword arguments of append_result.
        """
        return self.task_details


    def _get_required_keys(self) -> list[str]:
        """
        Get the required keys for the user query dictionary.

        Returns:
            list[str]: List of required keys.
        """
        return ["task_id", "prompt", "entry_point", "public_test", "private_test", "test_type"]


    def _get_fix_mode_query(self,
                            response: CompletedProcess,
                            meta_data: dict) -> str:
        """
        Check the error type of error returned and call the function for it.
        The chat history is never sent (see _call_fix_code), every query holds everything and has the same
        tagged sections, so the LLM can tell the parts apart, see FixQueryManager.
        - a wrong answer (AssertionError) on a public test: _assertion_error_query, BPD traces.
        - another error on a public test (crash, time limit): _other_error_query, the usual error messages.
        - the public tests pass but a hidden test fails: _hidden_test_query, a generic message.
        The error types go to self.error_handling.current_error_type, fix_code stores them.

        Args:
            response (CompletedProcess): Response from the container.
            meta_data (dict): The original user query (its prompt is the original question).

        Returns:
            str: The fix mode query.
        """
        results = self.harness.parse_test_results(response.stderr)
        if results is None:
            print_error(f"The driver did not print the test results (exit code {response.returncode}).")
            raise RuntimeError(
                f"The driver did not print the test results for task {meta_data['task_id']} "
                f"(exit code {response.returncode}).\n"
                f"stderr:\n{response.stderr}\nstdout:\n{response.stdout}"
            )

        number_of_public_tests = len(meta_data["public_test"])
        public_results = results[:number_of_public_tests]

        # all public tests passed
        if all(result == self.harness.PASS for result in public_results):
            return self._hidden_test_query(meta_data, results[number_of_public_tests:])

        messages, error_types = self.harness.concise_results(public_results)
        self.error_handling.current_error_type = error_types
        failed_count = sum(result != self.harness.PASS for result in public_results)
        print_info(f"{failed_count} of {number_of_public_tests} public tests failed")

        # wrong answer on a public test
        if any(self.harness.is_wrong_answer(result) for result in public_results):
            return self._assertion_error_query(meta_data, public_results, messages, error_types)

        # other error on a public test
        return self._other_error_query(meta_data, public_results, messages, error_types)


    def _assertion_error_query(self,
                               user_query: dict,
                               public_results: list[str],
                               messages: list[str],
                               error_types: list[str]) -> str:
        """
        At least one public test gave a wrong answer. The first wrong answers get a BPD trace, at most
        self.max_traces of them. The other wrong answers are listed with their input, expected and actual output,
        any other failed test is listed with its concise error message. The code is part of every trace, so the 
        manager only adds it on its own when there is no trace at all (BPD disabled or the code could not 
        be traced).

        Args:
            user_query (dict): The original user query.
            public_results (list[str]): One result per public test.
            messages (list[str]): The concise messages of public_results.
            error_types (list[str]): The error types of the failed public tests.
        """
        failures = []
        trace_count = 0
        for index, (result, message) in enumerate(zip(public_results, messages)):
            number = index + 1
            if result == self.harness.PASS:
                continue
            if self.harness.is_wrong_answer(result): # assertion
                trace = self._trace(user_query, index) if self.max_traces is None or trace_count < self.max_traces else None
                trace_count += trace is not None
                failures.append(Failure(number,
                                        WRONG_ANSWER,
                                        result.removeprefix('AssertionError: '),
                                        trace = trace))
            else:
                failures.append(Failure(number, ERROR, message))

        if trace_count:
            print_info(f"Added {trace_count} execution trace(s) to the fix mode query.")
        return self.fix_query.build(user_query["prompt"],
                                    self._last_code,
                                    self._summary(public_results, error_types),
                                    failures)


    def _other_error_query(self,
                           user_query: dict,
                           public_results: list[str],
                           messages: list[str],
                           error_types: list[str]) -> str:
        """
        No wrong answer, other errors (a crash, the time limit) on public tests.
        Every failed test is listed with its concise error message.

        Args:
            user_query (dict): The original user query.
            public_results (list[str]): One result per public test.
            messages (list[str]): The concise messages of public_results.
            error_types (list[str]): The error types of the failed public tests.
        """
        failures = [Failure(index + 1, ERROR, message)
                    for index, (result, message) in enumerate(zip(public_results, messages))
                    if result != self.harness.PASS]
        return self.fix_query.build(user_query["prompt"],
                                    self._last_code,
                                    self._summary(public_results, error_types),
                                    failures)


    def _hidden_test_query(self, user_query: dict, hidden_results: list[str]) -> str:
        """
        The public tests pass, a hidden test fails. Nothing about the hidden tests is shared except how many failed.
        One generic message, however many hidden tests fail.

        Args:
            user_query (dict): The original user query.
            hidden_results (list[str]): One result per hidden test.
        """
        self.error_handling.current_error_type = ["PrivateTestFailed"]

        failed_count = sum(result != self.harness.PASS for result in hidden_results)

        # Only for us, nothing of this is sent to the LLM: what kind of hidden tests fail?
        _, hidden_error_types = self.harness.concise_results(hidden_results)
        print_info(f"Public tests passed, {failed_count} of {len(hidden_results)} "
                   f"hidden tests failed: {dict(Counter(hidden_error_types))}")

        return self.fix_query.build(
            user_query["prompt"],
            self._last_code,
            f"Your solution passes the public tests but fails {failed_count} of {len(hidden_results)} hidden "
            "tests, so its logic is probably wrong or incomplete for inputs the examples do not cover."
        )


    def _summary(self, public_results: list[str], error_types: list[str]) -> str:
        """
        Summary of the public test results,
            e.g. "Your previous solution failed 2 of 5 public tests (AssertionError, NameError)."

        Args:
            public_results (list[str]): One result per public test.
            error_types (list[str]): The error types of the failed public tests.

        Returns:
            str: Summary message.
        """
        failed_count = sum(result != self.harness.PASS for result in public_results)
        return (f"Your previous solution failed {failed_count} of {len(public_results)} public tests "
                f"({', '.join(dict.fromkeys(error_types))}).")


    def _trace(self, user_query: dict, index: int) -> Optional[str]:
        """
        BPD trace of the latest code on public test `index` (0 based).
        Returns None if BPD is disabled or the code could not be traced.

        Args:
            user_query (dict): The original user query.
            index (int): Index of the public test to trace.
        
        Returns:
            Optional[str]: The BPD trace, or None if BPD is disabled or the code
        """
        if self.bpd is None:
            return None

        test = user_query["public_test"][index]
        entry_point = user_query["entry_point"] if user_query["test_type"] == "functional" else None
        trace = self.bpd.trace(self.harness.build_traceable_source(user_query, self._last_code),
                               test["input"],
                               entry_point,
                               test["output"])
        if trace is None:
            print_warning(f"No trace for public test {index + 1}: {self.bpd.last_error}")
            return None
        return trace.removeprefix(self.harness.PRELUDE.strip() + "\n")      # the typing import is not the LLM's code


    def _update_code(self, fix_mode_query: str, suppress_conversation_history: bool, meta_data: dict) -> None:
        data_point = meta_data.copy()
        data_point["prompt"] = fix_mode_query
        self._generate_code(data_point, suppress_conversation_history)


    def _call_fix_code(self, response: CompletedProcess, user_query: dict) -> tuple[int, int, list[str]]:
        # The history is always suppressed: every fix query has the problem, the previous code and the failures
        # in tagged sections, with the history the code and the problem would be sent twice.
        return self.fix_code(response, user_query, suppress_flag = True)


    def cleanup(self):
        super().cleanup()
        for file in [self.harness.SOLUTION_FILE_NAME, self.harness.PRIVATE_TESTS_FILE_NAME]:
            file_path = os.path.join(self.MOUNT_DIR, file)
            if os.path.exists(file_path):
                os.remove(file_path)
