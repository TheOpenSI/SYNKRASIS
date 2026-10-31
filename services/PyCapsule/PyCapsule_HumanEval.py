# =============================================================================================
# PyCapsule for HumanEval, the same as PyCapsule_BigCodeBench (same harness, prompts, fix queries and BPD traces).
# The only difference: the test code of HumanEval is one function check(candidate) with many asserts, it is split
# into a unittest class with one test per assert first (services/PyCapsule/humaneval_harness/split_check.py).
# The container needs no extra libraries, it can be the one of BigCodeBench (services/Container/prepare_bcb_container.py).
# =============================================================================================

import os
import sys

sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

from services.PyCapsule.PyCapsule_BigCodeBench import PyCapsule_BigCodeBench
from services.PyCapsule.humaneval_harness.split_check import split_check


class PyCapsule_HumanEval(PyCapsule_BigCodeBench):

    def _create_main_py(self, code: str, user_query: dict) -> None:
        unit_tests = split_check(user_query["test"], user_query["entry_point"])
        super()._create_main_py(code, {**user_query, "test": unit_tests})
