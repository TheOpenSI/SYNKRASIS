import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import json
import re
from typing import Dict, Optional, List
import pandas as pd

from utils.output_message_format.output_colour import print_warning, print_success
from data.DatasetBase import DatasetBase

class MBPP(DatasetBase):
    def __init__(self,
                 model_name: str,
                 file_path: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mbpp.jsonl"),
                 subset_size: Optional[int] = None,
                 output_dir: str = "experiment_results",
                 suffix: str = "",
                 is_resuming: bool = False) -> None:
        """
        Initialize the MBPP dataset loader.

        Args:
            file_path (str): Path to the JSONL file containing the dataset.
                             Defaults to 'mbpp.jsonl' in the current directory.
        """
        super().__init__(model_name, file_path, subset_size, output_dir, suffix, is_resuming)
        

    def _load_data(self) -> None:
        self.load_data_helper_json()
        
    
    def log_to_csv(self, model_name: str) -> None:
        self.log_to_csv_helper(column_names = ["task_id", "fix_mode_attempt_count", "status", "error_trace"])
        
        
    def process(self, data_point: dict) -> dict:
        function_signature = re.search(r"(?<=assert\s)(.*?)(?===)", data_point["test_list"][0])
        function_name = re.search(r".*\(", function_signature.group()).group() + ")"
        # Enforce function signature prompt
        enforce = (f"Please write a function named **'{function_name}'** to solve the following problem - \n")
        
        last_line = (f"An example function call will look like: '{function_signature.group().strip()}'. "
                     "You MUST keep the function name exactly as provided even if there's spelling error.")
        
        return {
            "task_id": data_point["task_id"],
            "prompt": enforce + data_point["text"] + "\n\n" + last_line,
            "entry_point": function_name.replace("()", ""),
            "test": data_point["test_list"]} # list of tests cases - list[str]
        
        
    def reset(self) -> None:
        """
        Reset all the fields.
        """
        super().reset()
        self.solved_count = 0
        self.unsolved_count = 0
        self.results = []
        

if __name__ == "__main__":
    mbpp = MBPP(model_name="test_model")
    for key, value in mbpp.get_next().items():
        print(f"{key}: {value}")