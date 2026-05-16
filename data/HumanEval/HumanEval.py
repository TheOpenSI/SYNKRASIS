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
                 file_path: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "human-eval-v2-20210705.jsonl"),
                 subset_size: Optional[int] = None):
        """
        Initialize the HumanEval dataset loader.

        Args:
            file_path (str): Path to the JSONL file containing the dataset.
                             Defaults to 'human-eval-v2-20210705.jsonl' in the current directory.
        """
        super().__init__(file_path, subset_size)
        self.solved_count: int = 0
        self.unsolved_count: int = 0
        self.results: List = []


    def _load_data(self) -> None:
        """
        Load the JSON data from the file.
        """
        self._load_json_data()


    def next(self) -> Optional[Dict[str, str]]:
        """
        Return the next datapoint.
        **Deprecated: Use process() instead.
        
        Returns:
            Optional[Dict[str, str]]: The next datapoint if available, else None.
        """
        if self.current_index < len(self.data):
            datapoint = self.data[self.current_index]
            self.current_index += 1
            
            # Create the test_code by combining the test and the check() call
            test_code = f"{datapoint['test']}\n\ncheck({datapoint['entry_point']})"
            time_complexity_test_code = re.search(r"assert.*$", 
                                                  test_code,
                                                  re.MULTILINE).group().strip().replace("candidate", datapoint["entry_point"])            
            return {
                "task_id": datapoint["task_id"],
                "prompt": datapoint["prompt"],
                "entry_point": datapoint["entry_point"],
                # "canonical_solution": datapoint["canonical_solution"], # not returning the solution
                "test": datapoint["test"],
                "time_complexity_test_code": time_complexity_test_code, # adding the first test case for time complexity
                "test_code": test_code
            }
        else:
            print_warning("No more datapoints available")
            return None
    

    def log_to_csv(self, model_name: str) -> None:
        """
        Write result data to CSV file using Pandas.
        For HumanEval task results.
        Args:
            model_name (str): Name of the LLM model to be used for the csv file.
        """
        df = pd.DataFrame(self.results, columns=["task_id", "fix_mode_attempt_count", "status"])
        df.to_csv(f"experiment_results/{model_name}_humaneval_results.csv", index = False)
        print_success(f"Results saved to {model_name}_results.csv")
        
        
    def process(self, data_point: dict) -> dict :
        """
        Process the data point to omit unnecessary fields.

        Returns:
            dict : Processed data point.
        """
          
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