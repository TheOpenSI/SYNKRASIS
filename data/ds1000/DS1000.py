import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import json
from typing import Dict, Optional, List
import pandas as pd

from utils.output_message_format.output_colour import print_warning, print_success

class DS1000Dataset:
    def __init__(self, 
                 file_path: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ds1000.jsonl")):
        """
        Initialize the DS1000 dataset loader.

        Args:
            file_path (str): Path to the JSONL file containing the dataset.
                             Defaults to 'ds1000_data.jsonl' in the current directory.
        """
        self.file_path = file_path
        self.data = []
        self.current_index = 0
        self.solved_count: int = 0
        self.unsolved_count: int = 0
        self.results: List = []
        self._load_data()


    def _load_data(self) -> None:
        """
        Load the JSON data from the file.
        """
        with open(self.file_path, "r") as file:
                self.data = [json.loads(line.strip()) for line in file]


    def next(self) -> Optional[Dict[str, str]]:
        """
        Return the next datapoint.

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
        Reset the index to 0.
        """
        self.current_index = 0
        self.solved_count = 0
        self.unsolved_count = 0
        self.results = []

    def __len__(self) -> int:
        """
        Return the number of datapoints in the dataset.

        Returns:
            int: The number of datapoints.
        """
        return len(self.data)

    def log_to_csv(self, model_name: str) -> None:
        """
        Write result data to CSV file using Pandas.
        For DS1000 task results.
        Args:
            model_name (str): Name of the model used for the results.
        """
        df = pd.DataFrame(self.results, columns=["problem_id", "library", "attempt_count", "status"])
        file_path = f"{os.path.dirname(os.path.abspath(__file__))}/{model_name}_ds1000_results.csv"
        df.to_csv(file_path, index=False)
        print_success(f"Results saved to {file_path}")