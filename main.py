import os
import sys
import json
import pandas as pd
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Services
from services.LLM.Ollama.Ollama import Ollama
from services.LLM.OpenAI_GPT.OpenAI_GPT import OpenAI_GPT
from services.DDI.DDI import DDI

# Utils
from utils.output_message_format.output_colour import print_model_output, print_info
from utils.output_message_format.output_colour import print_error, print_success, print_warning
from utils.resource.resource_mg_util import call_cleanup

def main():
    try:
        # Rebuttal 1
        # pc data
        norm_data_path = "DDI/data/norm_effect_data.json"
        with open(norm_data_path, "r") as f:
            norm_data = json.load(f)
        
        norm_effectiveness_key = ["E_0"]
        norm_effectiveness_key.extend([f"D_{i}"for i in range(1, 6)])
        
        # norm data preparation for ddi
        for entry in norm_data:
            model_name = entry["model"]
            for dataset in entry["effectiveness"]:
                dataset_name = dataset["dataset"]
                norm_effectiveness = {}
                for k, e in zip(norm_effectiveness_key,
                                         dataset["effectiveness"]): # normalised values
                    norm_effectiveness[k] = e
                # print(model_name, dataset_name, norm_effectiveness)
                
                ddi = DDI(file_path=norm_data_path, # placeholder
                          model_name=model_name,
                          maximum_debugging_attempts=5,
                          dataset=dataset_name,
                          output_dir="rebuttal")
                
                data = {}
                data["DDI"] = norm_effectiveness
                data["overall_success_percent"] = 80 # dummy
                result = ddi.get_DDI(data)
                # example result 
                # {'E_0': 37.953, 
                # 'lambda': 0.5483184795689318, 
                # 'fitted_E_0': 37.8391634098281, 
                # 'r_squared': 0.9960858321752506, 
                # 'theta': [50, 80, 90, 95, 99], 
                # 't_theta': [1.2641324456269878, 2.935224641159974, 4.199357086786962, 
                # 5.463489532413949, 8.398714173573923], 
                # 't_theta_ceiling': [2, 3, 5, 6, 9], 
                # 'fit_quality': 'excellent', 
                # 'A_phi': 80, 
                # 'normalised_effectiveness': {'E_0': 37.953, 'D_1': 22.115, 
                # 'D_2': 11.401, 'D_3': 7.434, 'D_4': 4.661, 'D_5': 3.717}}
                
                # print(model_name, "|", 
                #       dataset_name, "|", 
                #       f"Lambda: {result['lambda']}", "|",
                #       f"t_theta_ceiling: {result['t_theta_ceiling']}")
                print((f"{model_name:<20} | "
                       f"{dataset_name:<15} | "
                       f"Lambda: {result['lambda']:<20} | "
                       f"R²: {round(result['r_squared'], 4):<10} | "
                       f"t_theta: {[round(val, 4) for val in result['t_theta']]}"
                    #    f"t_theta: {[round(val, 4) for val in result['t_theta']]} | "
                    #    f"t_theta_ceiling: {result['t_theta_ceiling']}"
                       ))
            print("-"*80)
    
    except Exception as e:
        raise e
        
    finally:
        # Warning resource_tracker: There appear to be .* leaked semaphore objects"
        call_cleanup([])

if __name__ == '__main__':
    main()