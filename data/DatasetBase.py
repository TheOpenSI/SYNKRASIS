# ===================================================================================================================================
# Base class for Dataset Management and Processing
# 
# Child classes must implement the following methods:
#   - _load_data
#   - get_next
#   - log_to_csv
#   - process
#
# Fields:
#   - file_path (str): Path to the dataset file.
#   - subset_size (Optional[int]): Subset size of the dataset.
#   - data (List): Holds the dataset.
#   - results (List): Holds the results.
#   - current_index (int): Current index in the dataset.
#   - extractor (Extractor): Extractor object.
#   - regex_extractor (RegexExtractor): RegexExtractor object.
#
# Usage:
#   - reset (base class only resets the current_index)
#   - get_data_point_by_index (returns the EXACT data point without processing)
#   - load_data_helper_json (loads JSON data from self.file_path with specified subset size if provided)
#   - log_to_csv_helper (log_to_csv helper to log the results to a csv file)
#   - append_result_helper (helper function to append results to the results list)
#   - __len__
# ===================================================================================================================================

import os
import sys

sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import json
import pandas as pd
from typing import Optional, Any, List, Dict
from abc import ABC, abstractmethod

from utils.output_message_format.output_colour import print_error, print_warning, print_success, print_info
from utils.extractor.Extractor import Extractor
from utils.extractor.RegexExtractor import RegexExtractor


class DatasetBase(ABC):
    def __init__(self,
                 model_name: str,
                 file_path: str, 
                 subset_size: Optional[int] = None,
                 output_dir: str = "experiment_results",
                 suffix: str = "",
                 is_resuming: bool = False) -> None:
        """
        Initialize the dataset loader.

        Args:
            model_name (str): Name of the model to be used in the experiment, used for generating output file names.
            file_path (str): Path to the dataset file.
            subset_size (Optional[int]): Subset size of the dataset. 
                If None, the full dataset is used.
            output_dir (str): Directory to save the results. Defaults to "experiment_results".
            suffix (str): Suffix to append to the output file names, e.g. c2, fs.
                Start with '_'.
                Defaults to an empty string.
            is_resuming (bool): Whether to resume from a previous run. Defaults to False.
        """
        self.file_path: str = file_path
        self.model_name: str = model_name
        self.subset_size: Optional[int] = subset_size
        self.data: pd.DataFrame = []  # Holds the dataset
        self.results: list[dict] = []  # Holds the results
        self.current_index: int = 0  # Current index in the dataset
        self.solved_count: int = 0 # Number of solved tasks
        self.unsolved_count: int = 0 # Number of unsolved tasks
        self.output_dir: str = output_dir
        self.suffix: str = suffix  # Suffix to append to the output file names
        
        self.extractor = Extractor()
        self.regex_extractor = RegexExtractor()
        
        if os.path.exists(self.output_dir):
            print_info(f"Output directory exists: {self.output_dir}")
        else:
            os.makedirs(self.output_dir)
            print_info(f"Created output directory: {self.output_dir}")

        if is_resuming:
            print_info(f"Resuming from index {self.current_index}")
            saved_result_path = self.generate_file_path()
            # Loading previous data from the json file
            self.results = self._load_previous_results(saved_result_path + ".json")
            # Update solved and unsolved count based on the loaded results
            self.solved_count, self.unsolved_count = self._update_counts_from_results(self.results)
        
        self._load_data()


    @abstractmethod
    def _load_data(self) -> None:
        """
        Load data from self.file_path to self.data
        """
        pass


    @abstractmethod
    def log_to_csv(self) -> None:
        """
        Log the results to a csv file.
        """
        pass


    @abstractmethod
    def process(self, data_point: dict) -> dict:
        """
        Process the data point and add metadata. e.g. function signature.

        Args:
            data_point (dict): data point to process.

        Returns:
            data_point (dict): Processed data point.
        """
        pass
    
    def _update_counts_from_results(self, results: list[dict]) -> tuple[int, int]:
        """
        Update the solved and unsolved counts based on the loaded results.

        Args:
            results (list[dict]): List of results loaded from the json file.
        
        Returns:
            tuple[int, int]: Updated solved and unsolved counts.
        """
        try: 
            solved_count = sum(1 for result in results if result.get("status") == "pass")
            unsolved_count = sum(1 for result in results if result.get("status") == "fail")
            print_info(f"Updated solved count: {solved_count}, unsolved count: {unsolved_count}")
            return solved_count, unsolved_count
        except KeyError:
            print_warning("Key 'status' not found. Setting solved and unsolved counts to 0.")
            return 0, 0
    
    
    def _load_previous_results(self, file_path: str) -> list[dict]:
        """
        Load previous results from a json file.

        Args:
            file_path (str): Path to the json file. Should be the same as the one used in the previous run.
        
        Returns:
            list[dict]: List of results loaded from the json file.
        """
        if os.path.exists(file_path):
            with open(file_path, "r") as json_file:
                try:
                    results = json.load(json_file)
                    print_info(f"Loaded {len(results)} previous results from {file_path}")
                    self.current_index = len(results)  # Set current_index to the number of loaded results
                    print_info(f"Set current_index to {self.current_index}")
                    return results
                except json.JSONDecodeError:
                    print_warning(f"Failed to decode JSON from {file_path}. Starting with empty results.")
                    return []
        else:
            print_error(f"No previous results found at {file_path}.")
            raise FileNotFoundError(f"No previous results found at {file_path}.")
    
    
    def append_result(self, **kwargs) -> None:
        """
        Append the result to the results list.

        Args:
            **kwargs: Parameters to include in the result, typically containing:
                - task_id (int): Task ID
                - fix_mode_attempt_count (int): Number of fix mode attempts
                - status (str): Status of the fix mode attempt
                - Any additional parameters as needed
        """
        self.results.append(kwargs)


    def reset(self) -> None:
        """
        Reset the current_index to 0
        """
        self.current_index = 0


    def get_data_point_by_index(self, index: int) -> Optional[Any]:
        """
        Get a data point by index, returns the EXACT data point without processing.

        Args:
            index (int): Index of the data point to get.

        Returns:
            Optional[Any]: Data point, can be any file type.
        """
        try:
            return self.data.iloc[index]
        except IndexError:
            print_error(f"Index {index} out of range.")


    def load_data_helper_json(self) -> None:
        """
        _load_data helper.\n
        Loads JSON data from self.file_path with specified subset size.
        """
        with open(self.file_path, "r") as file:
            all_data = [json.loads(line.strip()) for line in file]

        self.data = all_data
            
            
    def log_to_csv_helper(self,
                          column_names: List[str]) -> None:
        """
        log_to_csv helper.\n
        Logs the results to a csv file.

        Args:
            column_names (List): List of column names for the csv file.
        """
        file_path = f"{self.generate_file_path()}.csv"
        df = pd.DataFrame(self.results, columns = column_names)
        df.to_csv(file_path, index = False)
        print_success(f"Results saved to {file_path}")


    def log_to_json(self) -> None:
        """
        Logs the results to a json file.
        """
        file_path = f"{self.generate_file_path()}.json"
        with open(file_path, "w") as json_file:
            json.dump(self.results, json_file, indent=4)
        print_success(f"Results saved to {file_path}.json")


    def generate_file_path(self) -> str:
        """
        Generate the file path for the result file without extension.
        """
        return f"{self.output_dir}/{self.model_name}_{self.__class__.__name__}_results{self.suffix}"


    def get_next(self) -> Optional[Dict[str, str]]:
        """
        Get the next(self.current_index) point from the dataset.\n
        Collects the data point, processes and returns.

        Returns:
            data_point (Optional[Dict[str, str]]): Processed next data point.
        """
        limit = self.subset_size if self.subset_size is not None else len(self.data)
        
        if self.current_index < limit:
            datapoint = self.data.iloc[self.current_index]
            self.current_index += 1
            
            # Process the data point
            return self.process(datapoint)
        else:
            print_warning("No more datapoints available")
            return None
            
            
    def __len__(self) -> int:
        """
        Return the number of datapoints in the dataset.

        Returns:
            int: The number of datapoints.
        """
        return len(self.data)

