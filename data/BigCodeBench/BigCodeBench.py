import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

from typing import Dict, Optional, List
import pandas as pd

from utils.output_message_format.output_colour import print_warning, print_success
from data.DatasetBase import DatasetBase
class BigCodeBench(DatasetBase):
    def __init__(self, 
                 file_path: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "v0.1.2-00000-of-00001.parquet"),
                 subset_size: Optional[int] = None):
        """
        Initialize the BigCodeBench dataset loader and load the data.

        Args:
            file_path (str): Path to the parquet file.
        """
        super().__init__(file_path, subset_size)
        self.solved_count: int = 0
        self.unsolved_count: int = 0
        self.results: List[dict] = []


    def _load_data(self) -> None:
        self.data = pd.read_parquet(self.file_path)


    def get_next(self) -> Optional[Dict[str, str]]:
        if self.current_index < len(self.data):
            datapoint = self.data.iloc[self.current_index]
            self.current_index += 1
            
            # Process the data point
            return self.process(datapoint)
        else:
            print_warning("No more datapoints available")
            return None
        
    
    def log_to_csv(self, model_name: str) -> None:
        super().log_to_csv_helper(model_name, 
                                  dataset_name = "BigCodeBench", 
                                  results = self.results,
                                  column_names = ["task_id", "fix_mode_attempt_count", "status"])
        
        
    def process(self, data_point: dict) -> dict :
        return {
            "task_id": data_point["task_id"].replace("/", "_"),
            "prompt": (data_point["instruct_prompt"] + "\n",
                       "The function signature and import statements are given below - \n",
                       data_point["complete_prompt"]),
            "entry_point": data_point["entry_point"],
            "test": data_point["test"],
            "libs": data_point["libs"],
            "metadata": data_point["doc_struct"],
        }
        
        
    def append_result(self, task_id: str, 
                      fix_mode_attempt_count: int,
                      status: str) -> None:
        """
        Append the experiment result to the results list.

        Args:
            task_id (str): Task ID.
            fix_mode_attempt_count (int): Debug attempt count.
            status (str): pass or fail.
        """
        self.results.append({
            "task_id": task_id,
            "fix_mode_attempt_count": fix_mode_attempt_count,
            "status": status
        })


    def reset(self) -> None:
        """
        Reset all the fields.
        """
        super().reset()
        self.solved_count = 0
        self.unsolved_count = 0
        self.results = []
        
