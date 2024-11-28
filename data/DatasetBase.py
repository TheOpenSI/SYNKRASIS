import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import json
from typing import Optional, Any
from abc import ABC, abstractmethod

from utils.output_message_format.output_colour import print_error, print_warning

class DatasetBase(ABC):
    def __init__(self, file_path: str, subset_size: Optional[int] = None):
        """
        Initialize the dataset loader.

        Args:
            file_path (str): Path to the dataset file.
        """
        self.file_path = file_path
        self.subset_size = subset_size
        self.data = [] # Holds the dataset
        self.current_index = 0 # Current index in the dataset
        self.extractor = Extractor() # Extracts function name
        self.regex_extractor = RegexExtractor() # Regex based extractors
        self._load_data()
        
    
    @abstractmethod    
    def _load_data(self) -> None:
        """
        Load data from data_file to self.data
        """
        pass
    
    
    @abstractmethod
    def next() -> Optional[Any]:
        """
        Get the next/self.current_index point from the dataset

        Returns:
            Optional[Dict[str, str]]: Data point.
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
        Process the data point and add metadata like function signature.
        Same as next().

        Args:
            data_point (dict): data point to process.

        Returns:
            dict: processed data point.
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
            return self.data[index]
        except IndexError:
            print_error(f"Index {index} out of range.")
            
            
    def __len__(self) -> int:
        """
        Return the number of datapoints in the dataset.

        Returns:
            int: The number of datapoints.
        """
        return len(self.data)
    
    
    def _load_json_data(self) -> None:
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