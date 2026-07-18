import pandas as pd
import glob
import json
from pathlib import Path


class QADataAnalyser:
    def __init__(self) -> None:
        self.data: list[pd.DataFrame] = self._load_data()
        self.available_services = self._get_all_available_services()
        
        
    def _load_data(self) -> list[pd.DataFrame]:
        script_dir = Path(__file__).parent.resolve()
        csv_files = glob.glob(str(script_dir / "*.csv"))
        
        return [pd.read_csv(file) for file in csv_files]
    
    
    def _get_all_available_services(self) -> list[str]:
        services = set()
        for df in self.data:
            df_services = self._get_available_services(df)
            services.update(df_services)
            
        return list(services)
    
    
    def _get_available_services(self, df: pd.DataFrame) -> list[str]:
        if 'service' in df.columns:
            available_services = df['service'].dropna().unique().tolist()
            # print(f"Found {len(available_services)} available services in DataFrame")
            
            return available_services
        
        else:
            raise ValueError("The DataFrame does not contain a 'service' column.")
        

if __name__ == "__main__":
    analyser = QADataAnalyser()