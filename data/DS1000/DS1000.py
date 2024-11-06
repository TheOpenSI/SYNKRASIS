import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import json
from typing import Dict, Optional, List
import pandas as pd

from utils.output_message_format.output_colour import print_warning, print_success
from data.DatasetBase import DatasetBase

class DS1000(DatasetBase):
    def __init__(self, 
                 file_path: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ds1000.jsonl"),
                 subset_size: Optional[int] = None):
        """
        Initialize the DS1000 dataset loader.

        Args:
            file_path (str): Path to the JSONL file containing the dataset.
                             Defaults to 'ds1000_data.jsonl' in the current directory.
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
            
            return datapoint
        else:
            print_warning("No more datapoints available")
            return None


    def reset(self) -> None:
        """
        Reset all fields.
        """
        self.current_index = 0
        self.solved_count = 0
        self.unsolved_count = 0
        self.results = []


    def log_to_csv(self, model_name: str) -> None:
        """
        Write result data to CSV file using Pandas.
        For DS1000 task results.
        Args:
            model_name (str): Name of the LLM model to be used for the csv file.
        """
        df = pd.DataFrame(self.results, columns=["problem_id", "library", "fix_mode_attempt_count", "status"])
        file_path = f"experiment_results/{model_name}_ds1000_results.csv" # save to a separate folder in the root directory
        df.to_csv(file_path, index=False)
        print_success(f"Results saved to {file_path}")
        
        
    def process(self, data_point: dict) -> dict:
        """
        Returns the same data point for DS1000.
        """
        # TODO: Add user prompt here if necessary
#         data_point["prompt"] = f"""
# Following is a problem statement for a data science problem.

# ### Instructions for Solution:
# 1. **Review Section A:** Identify all variables specified in section "A" of the problem statement. These variables already exist, so do not redefine them in the solution code.
# 2. **Write a Python function:** Using only the variables from Section "A", write a function that solves the problem as described in the statement.
# 3. **Call the function with Section A variables:** At the end of the function code, assign the result of the function call to a new variable `result`. Format it like this:

#     ```python
#     ### Solution
#     def generated_function(*args_from_section_A):
#         # Function implementation here

#     result = generated_function(*args_from_section_A)
#     ```
# {data_point["prompt"]}"""
        
        return data_point