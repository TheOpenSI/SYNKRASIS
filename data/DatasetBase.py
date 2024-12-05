# ===================================================================================================================================
# Base class for Dataset Management and Processing
# 
# Child classes must implement the following methods:
#   - _load_data
#   - get_next
#   - log_to_csv
#   - process
#
# Functions:
#   - reset (base class only resets the current_index)
#   - get_data_point_by_index (returns the EXACT data point without processing)
#   - load_data_helper_json (loads JSON data from self.file_path with specified subset size if provided)
#   - log_to_csv_helper (log_to_csv helper to log the results to a csv file)
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
    def __init__(self, file_path: str, subset_size: Optional[int] = None):
        """
        Initialize the dataset loader.

        Args:
            file_path (str): Path to the dataset file.
        """
        self.file_path = file_path
        self.subset_size = subset_size
        self.data = []  # Holds the dataset
        self.current_index = 0  # Current index in the dataset
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
        Collect the data point, process and return

        Returns:
            data_point (Optional[Dict[str, str]]): Processed next data point.
        """
        pass


    @abstractmethod
    def log_to_csv(self, model_name: str) -> None:
        """
        Log the results to a csv file.

        Args:
            model_name (str): Name of the model to be used as the title of the csv file.
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
                          column_names: List[str]) -> None:
        """
        log_to_csv helper.\n
        Logs the results to a csv file.

        Args:
            model_name (str): Name of the model to be used as the title of the csv file.
            dataset_name (str): Name of the dataset to be used as the title of the csv file.
            results (List): List of results to log.
            column_names (List): List of column names for the csv file.
        """
        df = pd.DataFrame(results, columns = column_names)
        df.to_csv(f"experiment_results/{model_name}_{dataset_name}_results.csv", index = False)
        print_success(f"Results saved to {model_name}_results.csv")    
            
            
    def __len__(self) -> int:
        """
        Return the number of datapoints in the dataset.

        Returns:
            int: The number of datapoints.
        """
        return len(self.data)

