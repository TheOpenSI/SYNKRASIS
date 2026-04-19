import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import pandas as pd
import ast
from typing import Dict, Optional, List

from utils.output_message_format.output_colour import print_warning, print_success
from data.DatasetBase import DatasetBase
class BigCodeBench(DatasetBase):
    def __init__(self,
                 model_name: str,
                 file_path: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "v0.1.2-00000-of-00001.parquet"),
                 subset_size: Optional[int] = None,
                 output_dir: str = "experiment_results",
                 suffix: str = "",
                 is_resuming: bool = False) -> None:
        super().__init__(model_name, file_path, subset_size, output_dir, suffix, is_resuming)


    def _load_data(self) -> None:
        self.data = pd.read_parquet(self.file_path)
    

    def log_to_csv(self) -> None:
        super().log_to_csv_helper(column_names = ["task_id", "fix_mode_attempt_count", "status", "error_trace"])
        
        
    def process(self, data_point: dict) -> dict :
        return {
            "task_id": data_point["task_id"].replace("/", "_"),
            "prompt": data_point["instruct_prompt"] + "\n\n" +
                      "The function signature, docstring and import statements are given below - \n" +
                      data_point["complete_prompt"],
            "entry_point": data_point["entry_point"],
            "test": data_point["test"],
            "libs": ast.literal_eval(data_point["libs"]),
            "metadata": data_point["doc_struct"],
        }
        
        
    def append_result(self, task_id: str, 
                      fix_mode_attempt_count: int,
                      status: str,
                      error_trace: list[str]) -> None:
        """
        Append the experiment result to the results list.

        Args:
            task_id (str): Task ID.
            fix_mode_attempt_count (int): Debug attempt count.
            status (str): pass or fail.
            error_trace (list[str]): List of error types encountered.
        """
        self.results.append({
            "task_id": task_id,
            "fix_mode_attempt_count": fix_mode_attempt_count,
            "status": status,
            "error_trace": error_trace
        })


    def reset(self) -> None:
        """
        Reset all the fields.
        """
        super().reset()
        self.solved_count = 0
        self.unsolved_count = 0
        self.results = []
        
