import pandas as pd
import json
import glob
from pathlib import Path
from collections import defaultdict

from services.LLM.LLMBase import LLMBase


class QueryAnalyser:
    def __init__(self,
                 llm: LLMBase,
                 service_desc_path: str = "data/QueryAnalyser/service_desc.json") -> None:
        self.llm = llm
        self.service_desc_path = service_desc_path
        self.service_descriptions = self._get_service_descriptions()
        self.system_prompt = self._get_system_prompt()
        self.llm.set_system_prompt(self.system_prompt)
        
        
    def _get_system_prompt(self) -> str:
        return (
            "You are a query router for a multi-service assistant system. "
            "On each turn you will be given a list of available services with short descriptions, followed by a user query. "
            "Decide which single service is best suited to handle that query, using only the descriptions provided for this turn "
            "Never assume a service exists beyond what is listed.\n\n"
            "Rules:\n"
            "- Match the query against the core intent of each service description, not just surface keywords.\n"
            "- If more than one service seems plausible, choose the one whose description is the more specific and direct match.\n"
            "- If none of the listed services are a reasonable match, respond with 'service -1'.\n"
            "- Respond with only the service name in the exact form - 'service $name', where 'name' is the exact name given for that service.\n"
            "Do not include any explanation or additional text."
        )

    
    
    def _get_service_descriptions(self) -> dict[str, str]:
        # script_dir = "/home/adnana/workspace/SYNKRASIS/data/QueryAnalyser"
        description_file_path = Path(self.service_desc_path).resolve()
        
        if not description_file_path.exists():
            raise FileNotFoundError(f"Service description file '{self.service_desc_path}' not found.")
        
        with open(description_file_path, "r") as f:
            return json.load(f)
        
        
    def _get_services(self,
                      df: pd.DataFrame) -> list[str]:
        if 'service' in df.columns:
            return df['service'].dropna().unique().tolist()
        
        else:
            raise ValueError("The DataFrame does not contain a 'service' column.")
        
        
    def _get_service_description(self,
                                 service_name: str) -> str:
        return self.service_descriptions[service_name]
    
    
    def _get_selected_service_descriptions(self,
                                       services: list[str]) -> dict[str, str]:
        return {service: self.service_descriptions[service] for service in services}
    
    
    def _generate_service_description_prompt(self,
                                             active_services: dict[str, str]) -> str:
        return "\n".join(
            f"- service {service_id}: {description}"
            for service_id, description in active_services.items()
        )
        
        
    def _generate_prompt(self,
                         service_prompt: str,
                         user_query: str) -> str:
        return (
            f"Services:\n{service_prompt}\n\n"
            f"Query: \"{user_query}\"\n\n"
            "Which service should handle this query?"
        )
        
        
    def _run_llm_inference(self,
                           file_name: str,
                           df: pd.DataFrame,
                           service_prompt: str) -> float:
        result = []
        correct_count = 0
        
        output_file = f"{self.llm.model_name}_{file_name}_query_analysis_results.json"
        output_path = Path(self.service_desc_path).parent.resolve() / "results" /output_file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        for _, row in df.iterrows():
            user_query = row['question']
            true_label = row['service']
            prompt = self._generate_prompt(service_prompt, user_query)
            response = self.llm.generate_response(prompt)
            is_correct = True if true_label in response else False
            
            if is_correct:
                correct_count += 1
                
            result.append({
                "question": user_query,
                "true_label": true_label,
                "predicted_label": response,
                "is_correct": is_correct
            })
            
            with open(output_path, "w") as f:
                json.dump(result, f, indent=4)
        
        accuracy = correct_count / len(df) if len(df) > 0 else 0
        print(f"Model: {self.llm.model_name} | Dataset: {file_name} | Accuracy: {accuracy:.2%} ({correct_count}/{len(df)})")
        
        return accuracy
        



    def run_test(self,
                 data_path: str = "data/QueryAnalyser") -> dict[str, dict[str, float]]:
        data_paths = glob.glob(f"{data_path}/*.csv")
        same_model_all_df_rsults = defaultdict(dict)
        for data_path in data_paths:
            file_name = Path(data_path).name
            print(f"Running test for {file_name}...")
            df = pd.read_csv(data_path)
            services_in_df = self._get_services(df)
            active_services = self._get_selected_service_descriptions(services_in_df)
            service_prompt = self._generate_service_description_prompt(active_services)
            accuracy = self._run_llm_inference(file_name, df, service_prompt)
            same_model_all_df_rsults[self.llm.model_name][file_name] = accuracy

        return same_model_all_df_rsults