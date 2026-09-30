import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import shutil

from subprocess import CompletedProcess

from services.PyCapsule.PyCapsuleBase import PyCapsuleBase
from services.Container.Container import Container
from services.LLM.LLMBase import LLMBase
from utils.code_parsing.code_parser import parse_response
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


    def _set_prompt_paths(self):
        return self.helper_set_prompt_paths()


    def _create_main_py(self, code: str, user_query: dict) -> None:
        suppress_warning = self.suppress_warning_code()
        