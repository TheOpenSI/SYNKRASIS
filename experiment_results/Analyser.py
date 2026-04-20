import pandas as pd
import json

from pathlib import Path

class ExperimentAnalyser:
    def __init__(self, file_path: str) -> None:
        self.file_path = Path(file_path)
        self.data: pd.DataFrame = self._load_data()
        
        
    def analyse(self):
        self._check_accuracy()
    
    
    def _check_accuracy(self) -> None:
        """
        Check pass accuracy.
        """
        # check the status column for pass/fail and calculate the accuracy
        if "status" not in self.data.columns:
            raise ValueError("The required column 'status' is missing in the data.")
        total_cases = len(self.data)
        passed_cases = len(self.data[self.data["status"] == "pass"])
        accuracy = passed_cases / total_cases if total_cases > 0 else 0
        print(f"Total Cases: {total_cases}, Passed Cases: {passed_cases}, Accuracy: {accuracy:.2%}")
        
        
        
    def _load_data(self) -> pd.DataFrame:
        file_extension = self.file_path.suffix
        if file_extension == ".json":
            with open(self.file_path, 'r') as f:
                data = json.load(f)
            return pd.DataFrame(data)
        
        elif file_extension == ".csv":
            return pd.read_csv(self.file_path)

        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
        
        
if __name__ == "__main__":
    analyser = ExperimentAnalyser(file_path="experiment_results/devstral:24b_BigCodeBench_results.json")
    analyser.analyse()