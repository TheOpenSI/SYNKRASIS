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
from typing import Optional, Any, List
from abc import ABC, abstractmethod

from utils.output_message_format.output_colour import print_error, print_warning, print_success
from utils.extractor.Extractor import Extractor
from utils.extractor.RegexExtractor import RegexExtractor


class DatasetBase(ABC):
    def __init__(self, 
                 file_path: str, 
                 subset_size: Optional[int] = None,
                 output_dir: str = "experiment_results",
                 suffix: str = "") -> None:
        """
        Initialize the dataset loader.

        Args:
            file_path (str): Path to the dataset file.
            subset_size (Optional[int]): Subset size of the dataset. 
                If None, the full dataset is used.
            output_dir (str): Directory to save the results. Defaults to "experiment_results".
            suffix (str): Suffix to append to the output file names, e.g. c2, fs.
                Start with '_'.
                Defaults to an empty string.
        """
        self.file_path: str = file_path
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
        
        self._load_data()


    @abstractmethod
    def _load_data(self) -> None:
        """
        Load data from self.file_path to self.data
        """
        pass


    @abstractmethod
    def get_next(self) -> Optional[Any]:
        """
        Get the next(self.current_index) point from the dataset.\n
        Collects the data point, processes and returns.

        Returns:
            data_point (Optional[Dict[str, str]]): Processed next data point.
        """
        pass


    @abstractmethod
    def log_to_csv(self, model_name: str) -> str:
        """
        Log the results to a csv file.

        Args:
            model_name (str): Name of the model to be used as the title of the csv file.
            
        Returns:
            str: Path to the saved csv file.
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

        if self.subset_size is not None:
            if self.subset_size > len(all_data):
                print_warning((f"Requested subset size {self.subset_size} is larger than dataset size {len(all_data)}. "
                              f"Using full dataset."))
                self.data = all_data
            else:
                self.data = all_data[:self.subset_size]
        else:
            self.data = all_data
            
            
    def log_to_csv_helper(self, model_name:str, 
                          dataset_name:str, 
                          results: List[dict],
                          column_names: List[str]) -> str:
        """
        log_to_csv helper.\n
        Logs the results to a csv file.

        Args:
            model_name (str): Name of the model to be used as the title of the csv file.
            dataset_name (str): Name of the dataset to be used as the title of the csv file.
            results (List): List of results to log.
            column_names (List): List of column names for the csv file.
        
        Returns:
            str: Path to the saved csv file.
        """
        df = pd.DataFrame(results, columns = column_names)
        result_file_path = f"{self.output_dir}/{model_name}_{dataset_name}_results{self.suffix}.csv"
        df.to_csv(result_file_path, index = False)
        print_success(f"Results saved to {model_name}_results.csv")
        
        return result_file_path
            
            
    def __len__(self) -> int:
        """
        Return the number of datapoints in the dataset.

        Returns:
            int: The number of datapoints.
        """
        return len(self.data)

