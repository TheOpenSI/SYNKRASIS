import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import base64
import pickle
import zlib
import json
import ast
import pandas as pd

from typing import Optional
from datetime import datetime, date

from data.DatasetBase import DatasetBase
from utils.output_message_format.output_colour import print_warning


class LiveCodeBench(DatasetBase):
    def __init__(self,
                 model_name: str,
                 file_path: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test6.jsonl"),
                 subset_size: Optional[int] = None,
                 output_dir: str = "experiment_results",
                 suffix: str = "",
                 is_resuming: bool = False,
                 start_date: Optional[str] = None,
                 end_date: Optional[str] = None) -> None:
        """
        Initialise the LiveCodeBench dataset loader.
        Link: https://huggingface.co/datasets/livecodebench/code_generation_lite/tree/main

        Args:
            model_name (str): The name of the model.

            file_path (str): Path to the JSONL file containing the dataset.
                             Defaults to 'livecodebench.jsonl' in the current directory.
            
            subset_size (Optional[int]): If provided, only load this many records from the dataset.

            output_dir (str): Directory to save the experiment results.

            suffix (str): Suffix to append to the output files.

            is_resuming (bool): If True, resume from a previous run.

            start_date (str): Optional start date in ISO format to filter records.

            end_date (str): Optional end date in ISO format to filter records.
        """
        self.start_date: Optional[date] = self._convert_date_format(start_date) if start_date else None
        self.end_date: Optional[date] = self._convert_date_format(end_date) if end_date else None
        self._is_valid_start_end_date()
        # stats
        self.total_records = 0
        self.file_max_date: Optional[date] = None
        self.file_min_date: Optional[date] = None

        super().__init__(model_name, file_path, subset_size, output_dir, suffix, is_resuming)
        self.filtered_records = len(self.data)


    def _is_valid_start_end_date(self) -> None:
        """
        Check if the provided start and end dates are valid.
        """
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date is later than end_date")



    def _convert_date_format(self, date_str: str) -> date:
        """
        Convert a date string to a date object. 
        The input date string is expected to be in ISO format.
        """
        return datetime.fromisoformat(date_str).date()


    def _load_data(self) -> None:
        records = []

        with open(self.file_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                self.total_records += 1
                data_point = self._process_json_line(line)
                if self._is_date_in_range(data_point["contest_date"]):
                    records.append(data_point)

        self.data = pd.DataFrame(records)
        if self.data.empty:
            print_warning("No records found in the requested date range.")


    def _process_json_line(self, line: str) -> dict:
        """
        Process a single line of JSON from the dataset file.

        Args:
            line (str): A line of JSON from the dataset file.
        """
        data_point = json.loads(line)
        data_point["contest_date"] = self._convert_date_format(data_point["contest_date"])
        self._update_file_date_range(data_point["contest_date"])
        return data_point


    def _update_file_date_range(self, contest_date: date) -> None:
        """
        Track the earliest and latest contest dates seen in the whole file, 
        regardless of any date filtering applied afterwards.

        Args:
            contest_date (date): The contest date of the current data point.
        """
        if self.file_min_date is None or contest_date < self.file_min_date:
            self.file_min_date = contest_date
        if self.file_max_date is None or contest_date > self.file_max_date:
            self.file_max_date = contest_date


    def log_to_csv(self) -> None:
        self.log_to_csv_helper(column_names = ["task_id", "fix_mode_attempt_count", "status", "error_trace"])


    def append_result(self, task_id: str,
                      fix_mode_attempt_count: int,
                      status: str,
                      error_trace: list[str]) -> None:
        """
        LiveCodeBench task ids are strings (e.g. abc387_b), the base class converts them to int.
        """
        self.results.append({
            "task_id": str(task_id),
            "fix_mode_attempt_count": int(fix_mode_attempt_count),
            "status": status,
            "error_trace": error_trace
        })


    def _build_prompt(self, question: str, starter_code: str, test_type: str) -> str:
        """
        Build the prompt, follows the LiveCodeBench code generation prompt format.
        Starter code is present only when the tests are functional.
        """
        if test_type == "functional":
            return (f"{question}\n\n"
                    "You will use the following starter code to write the solution to the problem.\n"
                    f"```python\n{starter_code}\n```")

        return (f"{question}\n\n"
                "Read the input from standard input and write the answer to standard output. "
                "The code must be a complete standalone program, do not hard code the sample inputs.")


    def process(self, data_point: pd.Series) -> dict :
            metadata = ast.literal_eval(data_point["metadata"])
            public_test_cases = json.loads(data_point["public_test_cases"])
            test_type = self._get_test_type(public_test_cases)
            return {
                "task_id": data_point["question_id"],
                "prompt": self._build_prompt(data_point["question_content"], data_point["starter_code"], test_type),
                "entry_point": metadata.get("func_name", None), # relevant when starter code is present, test is functional.
                "public_test": public_test_cases,
                "private_test": self._decode_test_cases(data_point["private_test_cases"]),
                "starter_code": data_point["starter_code"],
                "test_type": test_type,
                "metadata": data_point["metadata"]
            }


    def _get_test_type(self, tests: list[dict] | dict) -> str:
        """
        Determine the test type from the provided tests.
        
        Args:
            tests (list[dict] | dict): A list of test case dictionaries or a single test case dictionary.
        
        Returns:
            str: The test type if all test cases have the same type, otherwise "Multi".
        """
        return tests[0]["testtype"] if isinstance(tests, list) else tests["testtype"]


    def _is_date_in_range(self, contest_date: date) -> bool:
        """
        Check whether a date lies within the start and end dates (inclusive).
        A missing bound means no limit on that side.

        Args:
            contest_date (date): The date to check.

        Returns:
            bool: True if the date is within the range, False otherwise.
        """
        if self.start_date is not None and contest_date < self.start_date:
            return False
        if self.end_date is not None and contest_date > self.end_date:
            return False
        return True


    def _decode_test_cases(self, encoded: str) -> str:
        """Turn an encoded private_test_cases value back into a string."""
        # Step 1: base64 text -> compressed bytes
        compressed = base64.b64decode(encoded)

        # Step 2: compressed bytes -> raw bytes
        raw = zlib.decompress(compressed)

        # Step 3: raw bytes -> string
        # Pickle data starts with the byte 0x80, so we check for that.
        if raw[:1] == b"\x80":
            # Only unpickle data from a source you trust.
            return pickle.loads(raw)

        return raw.decode("utf-8")


    def get_stat(self) -> str:
        """
        Print the statistics of the dataset, including total records, filtered records, and date range.
        """
        stat = f"Total records in file: {self.total_records}\n"
        stat += f"Filtered records based on date range: {self.filtered_records}\n"
        if self.file_min_date and self.file_max_date:
            stat += f"Date range in file: {self.file_min_date} to {self.file_max_date}\n"
        if self.start_date or self.end_date:
            stat += (f"Date range applied for filtering: {self.start_date or self.file_min_date} "
                     f"to {self.end_date or self.file_max_date}\n")

        # starter code count
        starter_code_count = (self.data["starter_code"] != "").sum()
        stat += f"Data points with starter code: {starter_code_count}\n"

        # meta data count
        meta_data_count = (self.data["metadata"] != "{}").sum()
        stat += f"Data points with meta data: {meta_data_count}\n"

        # test types
        all_test_types = [
            self._test_type_stat(ast.literal_eval(entry))
            for entry in self.data["public_test_cases"].to_list()
        ]
        test_types = set(all_test_types)
        test_type_counts = pd.Series(all_test_types).value_counts()
        stat += f"Test types: {', '.join(test_types)}\n"
        stat += "Test type counts -\n"
        for test_type, count in test_type_counts.items():
            stat += f"  {test_type}: {count}\n"
        stat += f"Total data points with multiple test types: {all_test_types.count('Multi')}\n"
        
        return stat


    def _test_type_stat(self, test_cases: list[dict]) -> str:
        """
        Check if all test cases have the same test type.

        Args:
            test_cases (list[dict]): A list of test case dictionaries.

        Returns:
            str: The test type if all test cases have the same type, otherwise "Multi".
        """
        test_types = [test_case["testtype"] for test_case in test_cases]
        is_same_test_type = len(set(test_types)) == 1
        if not is_same_test_type:
            return "Multi"
        return test_types.pop()