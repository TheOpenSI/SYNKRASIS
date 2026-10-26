# =============================================================================================
# Fix query manager.
# Builds the query for a fix mode attempt. The query is self-contained (the chat history is not
# sent), the parts are in tagged sections so the LLM can tell where each one starts and ends:
#
#   <problem>            the original question
#   <previous_code>      the latest code (left out when a trace is given, the trace has the code)
#   <test_failures>      the summary, and one <test_failure test="n"> for every failed test
#                        without a trace: a wrong answer (input, expected and actual output)
#                        or another error (its message)
#   <execution_traces>   one <trace test="n"> for every wrong answer that has a trace
#   <task>               what the LLM has to do
#
# The manager only builds text. Dataset specific parts (the failures, the traces, the summary)
# are given by the PyCapsule class of the dataset.
#
# Usage:
# - FixQueryManager(legend: str = "", task: str = REDERIVE_TASK)
# - build(problem: str, code: str, summary: str, failures: list[Failure] = None) -> str
#       The fix mode query.
# - section(tag: str, content: str, **attributes) -> str
#       The content between an opening and a closing tag.
# =============================================================================================

from dataclasses import dataclass
from typing import Optional

WRONG_ANSWER = "wrong_answer"
ERROR = "error"


@dataclass
class Failure:
    """
    A failed test.

    Args:
        test (int): Number of the test (1 based).
        kind (str): WRONG_ANSWER (the code ran and the output differs) or ERROR (a crash, the time limit...).
        message (str): WRONG_ANSWER: the input, expected output and actual output.
            ERROR: the concise error message.
        trace (Optional[str]): Execution trace of the code on this test, only for a WRONG_ANSWER.
    """
    test: int
    kind: str
    message: str
    trace: Optional[str] = None


class FixQueryManager:
    # Lead-ins of the failed tests in <test_failures>.
    ANSWER_INTRO = "Following is the test cases that failed with the expected and actual output:"
    ERROR_INTRO = "Following is the error message(s) of the failed public test(s). Fix the code accordingly."

    # The instruction for crashes, time limits and hidden tests (no wrong answer on a public test).
    REDERIVE_TASK = ("Re-derive the approach from the problem statement instead of patching the examples, then check: "
                     "minimum/maximum constraint values and tiny inputs, duplicates and ties, time complexity at the "
                     "maximum input size, and the exact output format.\n"
                     "Rewrite the whole solution.")

    # The instruction for a wrong answer without a trace, the same idea as TRACE_TASK: fix it, do not start over.
    WRONG_ANSWER_TASK = ("Do not start over. Your code ran but printed a different output than expected on the failing "
                         "test(s). Compare your output with the expected output, find the part of your code that causes "
                         "the difference, say in one sentence what it should do instead, and change only what is needed "
                         "to fix it. Keep the rest of the code as it is. Then give the complete corrected code.")

    # The instruction when there is a trace (it replaces REDERIVE_TASK): fix what the trace shows, do not start over.
    TRACE_TASK = ("Do not start over. The trace shows what your code did on a failing test. Go through the trace line by "
                  "line and compare each value with what the expected output requires. Find the first line whose value "
                  "is wrong, say in one sentence what that line should have computed, and change only what is needed to "
                  "fix it. Keep the rest of the code as it is. Then give the complete corrected code.")

    def __init__(self,
                 legend: str = "",
                 task: str = REDERIVE_TASK,
                 trace_task: str = TRACE_TASK,
                 wrong_answer_task: str = WRONG_ANSWER_TASK,
                 answer_intro: str = ANSWER_INTRO,
                 error_intro: str = ERROR_INTRO) -> None:
        """
        Args:
            legend (str, optional): Explains how to read a trace, added once before the traces.
                Defaults to "" (nothing is added).
            task (str, optional): The instruction in <task> for crashes, time limits and hidden tests.
                Defaults to REDERIVE_TASK.
            trace_task (str, optional): The instruction in <task> when there is a trace. Defaults to TRACE_TASK.
            wrong_answer_task (str, optional): The instruction in <task> for a wrong answer without a trace.
                Defaults to WRONG_ANSWER_TASK.
            answer_intro (str, optional): The lead-in of the wrong answers without a trace in <test_failures>.
                Defaults to ANSWER_INTRO.
            error_intro (str, optional): The lead-in of the other errors in <test_failures>. Defaults to ERROR_INTRO.
        """
        self.legend = legend
        self.task = task
        self.trace_task = trace_task
        self.wrong_answer_task = wrong_answer_task
        self.answer_intro = answer_intro
        self.error_intro = error_intro


    def build(self,
              problem: str,
              code: str,
              summary: str,
              failures: Optional[list[Failure]] = None) -> str:
        """
        The fix mode query.
        The code is left out when at least one failure has a trace, a trace contains the code.

        Args:
            problem (str): The original question.
            code (str): The latest code.
            summary (str): The first lines of <test_failures>,
                e.g. "Your previous solution failed 3 of 3 public tests (AssertionError)."
            failures (list[Failure], optional): The failed tests. Defaults to None (only the summary).

        Returns:
            str: The fix mode query.
        """
        failures = failures or []
        traced = [failure for failure in failures if failure.trace is not None]
        wrong_answers = [failure for failure in failures
                         if failure.kind == WRONG_ANSWER and failure.trace is None]
        errors = [failure for failure in failures if failure.kind == ERROR]

        failure_parts = [summary]
        if wrong_answers:
            failure_parts.append(self.answer_intro + "\n\n" + self._failure_elements(wrong_answers))
        if errors:
            failure_parts.append(self.error_intro + "\n\n" + self._failure_elements(errors))

        sections = [self.section("problem", problem)]
        if not traced:
            sections.append(self._code_section(code))      # no trace: the code has to be sent on its own
        # the summary, then each group of failures after a blank line
        failure_text = failure_parts[0] + ("\n" + "\n\n".join(failure_parts[1:]) if len(failure_parts) > 1 else "")
        sections.append(self.section("test_failures", failure_text))

        if traced:
            sections.append(self.section("execution_traces", self._traces_text(traced)))
            task = self.trace_task
        elif any(failure.kind == WRONG_ANSWER for failure in failures):
            task = self.wrong_answer_task
        else:
            task = self.task
        sections.append(self.section("task", task))
        return "\n\n".join(sections)


    def _failure_elements(self, failures: list[Failure]) -> str:
        return "\n\n".join(self.section("test_failure", failure.message, test=failure.test)
                           for failure in failures)


    def _traces_text(self, traced: list[Failure]) -> str:
        """
        The lead-in, the legend (once) and one <trace> per failure, each with the failed input, the expected
        and actual output, then the trace.
        """
        text = "Following is your previous solution with an execution trace.\n"
        if self.legend:
            text += self.legend + "\n"
        traces = "\n\n".join(self.section("trace", f"{failure.message}\n{failure.trace}", test=failure.test)
                             for failure in traced)
        return text + "\n" + traces


    def _code_section(self, code: str) -> str:
        return self.section("previous_code", f"```python\n{code}\n```")


    @staticmethod
    def section(tag: str, content: str, **attributes) -> str:
        """
        The content between an opening and a closing tag, e.g. <trace test="1">...</trace>.
        The LLM sees where every part starts and ends.

        Args:
            tag (str): Name of the tag.
            content (str): Content of the section.
            **attributes: Attributes of the opening tag, e.g. test=1.
        """
        attribute_text = "".join(f' {name}="{value}"' for name, value in attributes.items())
        return f"<{tag}{attribute_text}>\n{content}\n</{tag}>"
