import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

from typing import Dict, Optional, List, Union
import pandas as pd

from utils.output_message_format.output_colour import print_warning, print_error
from data.DatasetBase import DatasetBase
class HumanEval(DatasetBase):
    def __init__(self, 
                 file_path: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                               "humaneval.jsonl"),
                 subset_size: Optional[int] = None):
        """
        Initialize the HumanEval dataset loader.

        Args:
            file_path (str): Path to the JSONL file containing the dataset.
                             Defaults to 'human-eval-v2-20210705.jsonl' in the current directory.
        """
        super().__init__(file_path, subset_size)


    def _load_data(self) -> None:
        # Using the helper function to load the JSON data
        self.load_data_helper_json()


    def get_next(self) -> Union[Dict[str, str], None]:
        if self.current_index < len(self.data):
            datapoint = self.data[self.current_index]
            self.current_index += 1
            
            return self.process(datapoint)
        else:
            print_warning("No more datapoints available")
            return None


    def reset(self) -> None:
        """
        @override
        Resetting all the fields.
        """
        self.current_index = 0
        self.solved_count = 0
        self.unsolved_count = 0
        self.results = []
    

    def log_to_csv(self, model_name: str) -> str:
        return self.log_to_csv_helper(model_name=model_name,
                               dataset_name="HumanEval",
                               results=self.results,
                               column_names=["task_id", "fix_mode_attempt_count", "status"])
        
        
    def process(self, data_point: dict) -> dict :
        """
        Process the data point to omit unnecessary fields.

        Returns:
            dict : Processed data point.
        """
          
        return {
            "task_id": data_point["task_id"],
            "prompt": data_point["prompt"],
            "entry_point": data_point["entry_point"],
            "test": data_point["test"]
        }
    
        