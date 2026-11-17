import json
from pathlib import Path
from collections import defaultdict


class Consolidator:
    def __init__(self) -> None:
        self.metadata_folder = Path("Agents/data/metadata")

    
    def _collect_all_files(self) -> list[Path]:
        return self.metadata_folder.glob("*.json")
    

    def consolidate(self) -> None:
        data_files = self._collect_all_files()
        
        consolidated_data = defaultdict(dict)
        for file in data_files:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for case_id, record in data.items():
                consolidated_data[case_id].update(record)
        
        with open("Agents/data/metadata/Consolidated_metadata.json", "w", encoding="utf-8") as f:
            json.dump(consolidated_data, f, indent=4)
        

if __name__ == "__main__":
    consolidator = Consolidator()
    consolidator.consolidate()