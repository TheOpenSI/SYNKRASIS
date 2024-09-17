import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/..")

import json
import re
from typing import Dict, Optional

from utils.output_message_format.output_colour import print_warning

class HumanEvalDataset:
    def __init__(self, 
                 file_path: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "human-eval-v2-20210705.jsonl")):
        """
        Initialize the HumanEval dataset loader.

        Args:
            file_path (str): Path to the JSONL file containing the dataset.
                             Defaults to 'human-eval-v2-20210705.jsonl' in the current directory.
        """
        self.file_path = file_path
        self.data = []
        self.current_index = 0
        self._load_data()


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
            
            # Create the test_code by combining the test and the check() call
            test_code = f"{datapoint['test']}\n\ncheck({datapoint['entry_point']})"
            time_complexity_test_code = re.search(r"(assert[\s\S]*?)(?=assert\s|$)", 
                                                test_code).group(0).strip().replace("candidate", datapoint["entry_point"])            
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


    def reset(self) -> None:
        """
        Reset the index to 0.
        """
        self.current_index = 0


    def __len__(self) -> int:
        """
        Return the number of datapoints in the dataset.

        Returns:
            int: The number of datapoints.
        """
        return len(self.data)