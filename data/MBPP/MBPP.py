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
                 file_path: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mbpp.jsonl")):
        """
        Initialize the HumanEval dataset loader.

        Args:
            file_path (str): Path to the JSONL file containing the dataset.
                             Defaults to 'human-eval-v2-20210705.jsonl' in the current directory.
        """
        super().__init__(file_path)
        self.solved_count: int = 0
        self.unsolved_count: int = 0
        self.results: List[Dict[int, int, str]] = [] # task_id, fix_mode_attempt_count, status 


    def _load_data(self) -> None:
        """
        Load the JSON data from the file.
        """
        try:
            with open(self.file_path, "r") as file:
                self.data = [json.loads(line.strip()) for line in file]
        except FileNotFoundError:
            print_warning(f"File not found: {self.file_path}")
        except json.JSONDecodeError:
            print_warning(f"Invalid JSON in file: {self.file_path}")


    def next(self) -> Optional[Dict[str, str]]:
        """
        Return the next datapoint.

        Returns:
            Optional[Dict[str, str]]: The next datapoint if available, else None.
        """
        if self.current_index < len(self.data):
            datapoint = self.data[self.current_index]
            self.current_index += 1
            
            function_signature = re.search(r"(?<=assert\s)(.*?)(?=\s==)", datapoint["test_list"][0])
            function_signature_prompt = "A typical function call will have the following function signature - \n" + function_signature.group()
           
            return {
                "task_id": datapoint["task_id"],
                "prompt": datapoint["text"] + "\n" + function_signature_prompt,
                "test_list": datapoint["test_list"]
            }
        else:
            print_warning("No more datapoints available")
            return None


    def reset(self) -> None:
        """
        Reset all the variables.
        """
        super().reset()
        self.solved_count = 0
        self.unsolved_count = 0
        self.results = []
    

    def log_to_csv(self, model_name: str) -> None:
        """
        Write result data to CSV file using Pandas.
        For MBPP task results.
        Args:
            model_name (str): Name of the model used to generate the results.
        """
        df = pd.DataFrame(self.results, columns=["task_id", "fix_mode_attempt_count", "status"])
        df.to_csv(f"{os.path.dirname(os.path.abspath(__file__))}/{model_name}_results.csv", index = False)
        print_success(f"Results saved to {model_name}_results.csv")