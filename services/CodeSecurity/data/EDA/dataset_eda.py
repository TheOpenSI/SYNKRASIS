import json
from typing import DefaultDict, Optional
from pathlib import Path

class DatasetEDA:
    def __init__(self, 
                 dataset_path: str,
                 cwe_id_extract_function: callable,
                 cwe_key: str) -> None:
        self.dataset_path = dataset_path
        self.EDA_PATH = "services/CodeSecurity/cwe_analysis/eda_results.json"
        self.data: list = self._load_data(self.dataset_path)
        self.eda: dict = self._load_data(self.EDA_PATH)
        self.cwe_id_extract_function = cwe_id_extract_function
        self.cwe_key = cwe_key


    def _load_data(self, file_path: str):
        file_name = Path(file_path).name
        if file_name.endswith(".jsonl"):
            return self._load_jsonl(file_path)
        elif file_name.endswith(".json"):
            return self._load_json(file_path)
        else:
            raise ValueError("Unsupported file format. Only .jsonl and .json are supported.")


    def _load_jsonl(self, file_path: str) -> list:
        with open(file_path, "r") as f:
            jsonl_data = [json.loads(line) for line in f]
        return jsonl_data
    

    def _load_json(self, file_path: str):
        with open(file_path, "r") as f:
            json_data = json.load(f)
        return json_data
    
    
    def run_data_eda(self) -> None:
        print(self._get_cwe_type_distribution())
                
                
    def _get_cwe_type_distribution(self) -> dict:
        cwe_type_distribution = DefaultDict(int)
        
        for entry in self.data:    
            id = self.cwe_id_extract_function(entry[self.cwe_key])
            try:
                eda = self.eda[id]
                cwe_type = eda["type"]
                cwe_type_distribution[cwe_type] += 1
            except KeyError:
                print(f"Missing EDA results for CWE ID: {id}")
        
        return dict(cwe_type_distribution)


if __name__ == "__main__":
    get_cwe_id_sven = lambda text: str(int(text.split("-")[-1]))
    get_cwe_id_seceval = lambda text: str(int(text.split("_")[0].split("-")[-1]))
    
    seceval_dataset_path = "services/CodeSecurity/data/SecurityEval.jsonl"
    sven_dataset_path = "services/CodeSecurity/data/SVEN_python.json"

    for dataset_path, cwe_id_extract_function, cwe_key in \
        [(seceval_dataset_path, get_cwe_id_seceval, "ID"), 
                         (sven_dataset_path, get_cwe_id_sven, "vul_type")]:
        eda = DatasetEDA(
            dataset_path=dataset_path,
            cwe_id_extract_function=cwe_id_extract_function,
            cwe_key=cwe_key
        )
        print(f"EDA results for dataset: {dataset_path}")
        eda.run_data_eda()
        print("\n")