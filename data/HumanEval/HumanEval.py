import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/..")

import json
import re
from typing import Dict, Optional, List
import pandas as pd

from utils.output_message_format.output_colour import print_warning, print_success
from data.DatasetBase import DatasetBase
class HumanEval(DatasetBase):
    def __init__(self,
                 model_name: str,
                 file_path: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "human-eval-v2-20210705.jsonl"),
                 subset_size: Optional[int] = None,
                 output_dir: str = "experiment_results",
                 suffix: str = "",
                 is_resuming: bool = False) -> None:
        """
        Initialize the HumanEval dataset loader.

        Args:
            file_path (str): Path to the JSONL file containing the dataset.
                             Defaults to 'human-eval-v2-20210705.jsonl' in the current directory.
        """
        super().__init__(model_name, file_path, subset_size, output_dir, suffix, is_resuming)


    def _load_data(self) -> None:
        self.load_data_helper_json()
    

    def log_to_csv(self) -> None:
        self.log_to_csv_helper(column_names = ["task_id", "fix_mode_attempt_count", "status", "error_trace",
                                               "tests_passed"])


    def append_result(self, task_id: str,
                      fix_mode_attempt_count: int,
                      status: str,
                      error_trace: list[str],
                      tests_passed: Optional[list[str]] = None) -> None:
        """
        Also stores how many of the unit tests passed at every attempt, e.g. ["2/5", "5/5"]
        (0 is the initial generation, then the fix attempts).
        """
        self.results.append({
            "task_id": int(task_id),
            "fix_mode_attempt_count": int(fix_mode_attempt_count),
            "status": status,
            "error_trace": error_trace,
            "tests_passed": tests_passed or []
        })


    def select_tasks(self, task_ids: list[int]) -> None:
        """
        Keep only these tasks, in the order of the dataset. get_next and resuming then work on this subset,
        so a run can be restricted to some tasks, e.g. the ones another run failed.
        Call it before the run starts, a resumed run counts its position in the subset.

        Args:
            task_ids (list[int]): Task ids, the number in "HumanEval/<number>".
        """
        wanted = {int(task_id) for task_id in task_ids}
        self.data = self.data[self.data["task_id"].map(self._process_task_id).isin(wanted)].reset_index(drop = True)
        
        
    def process(self, data_point: dict) -> dict :
        return {
            "task_id": self._process_task_id(data_point["task_id"]),
            "prompt": data_point["prompt"],
            "entry_point": data_point["entry_point"],
            "test": data_point["test"]
        }
        
        
    def _process_task_id(self, task_id: str) -> int:
        """
        Extract the task id from the given task_id string.
        For HumanEval, the task_id is in the format "human_eval/{task_id}".

        Args:
            task_id (str): The original task_id string.

        Returns:
            int: The extracted task id.
        """
        return int(task_id.split("/")[-1])


    def reset(self) -> None:
        """
        Reset all the fields.
        """
        self.current_index = 0
        self.solved_count = 0
        self.unsolved_count = 0
        self.results = []