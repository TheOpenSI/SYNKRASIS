import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import pandas as pd
from typing import Dict, Optional, List
from deprecated import deprecated

from utils.output_message_format.output_colour import print_warning, print_success
from modules.SignatureConverter import SignatureConverter
from data.DatasetBase import DatasetBase

class MBPP(DatasetBase):
    def __init__(self, 
                 file_path: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                               "mbpp_main.jsonl"),
                 subset_size: Optional[int] = None):
        """
        Initialize the MBPP dataset loader.

        Args:
            file_path (str): Path to the JSONL file containing the dataset.
                             Defaults to 'mbpp.jsonl' in the current directory.
        """
        super().__init__(file_path, subset_size)


    def _load_data(self) -> None:
        # Using the helper function to load the JSON data
        self.load_data_helper_json()


    @deprecated("Use process() instead in release.")
    def get_next(self) -> Optional[Dict[str, str]]:
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
        Reset all the fields.
        """
        super().reset()
        self.solved_count = 0
        self.unsolved_count = 0
        self.results = []
    

    def log_to_csv(self, model_name: str) -> None:
        self.log_to_csv_helper(model_name=model_name,
                               dataset_name="MBPP",
                               results=self.results,
                               column_names=["task_id", "fix_mode_attempt_count", "status"])        
    
        
    def process(self, data_point: dict) -> dict:
        # Example function call from test case
        function_call = self.regex_extractor.extract_function_call_from_test_case(data_point["test_list"][0])
        
        # Patch: Data point 768 and 926 have function calls starting with "("
        function_call = self.extractor.remove_leading_bracket(function_call)
        
        # Remove the type casting from function call if present, e.g. int(foo(1, 2))
        function_call = self.regex_extractor.extract_function_call_from_type_cast(function_call)
        
        # Extracting the actual function name from test_case
        function_name = self.extractor.get_function_name_from_call(function_call) + "()"
        
        # Function signature
        function_signature = SignatureConverter.convert(call_string=function_call)
        
        # Enforce function signature prompt
        function_signature_prompt = (f"### Required function name for your refernce **'{function_name}'**.\n"
                                     f"### Function Signature for your reference - {function_signature}\n"
                                     f"### An example function call from private test cases - {function_call}\n") 
        
        return {
            "task_id": data_point["task_id"],
            "prompt": data_point["text"] + "\n" + function_signature_prompt,
            "test_list": data_point["test_list"],
            "function_name": function_name,
            "function_signature": function_signature,
            "function_call": function_call}