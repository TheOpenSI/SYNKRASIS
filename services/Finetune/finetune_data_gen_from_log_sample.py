# Sample code to generate finetune data from a log file.
# This code reads a log file, extracts questions and answers, and saves them to a CSV
# For log files, look into pycapsule_experiments branch.
# ==========================================================================================

# import os
# import sys
# sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

# import re
# import pandas as pd
# from datasets import load_dataset

# from utils.output_message_format.output_colour import print_success
# from services.Finetune.sample_dataset_formatting_func import formatting_func


# def generate_finetune_data(file_path:str) -> None:
#     with open(file_path) as f:
#         data = f.read()

#     question_pattern = r"#{10}\n\[FINAL\sPROMPT\]\sUser:\s(.*?)\n#{10}"
#     answer_pattern = r"(?<=\[GPT-3\.5-TURBO\]).*?(### Step-by-step reasoning.*?)(?=\[SUCCESS\])"

#     question = re.findall(question_pattern, data, re.DOTALL)
#     answer = re.findall(answer_pattern, data, re.DOTALL)
#     answer = [a[:-5] for a in answer]
#     print(len(question))
#     print(len(answer))
    
#     # Keeping 50 samples for finetuning
#     question = question[:50]
#     answer = answer[:50]

#     pd.DataFrame({"Question": question, "Answer": answer}).to_csv("/home/s448780/workspace/synkrasis_master/services/Finetune/mbpp_finetune_data.csv", index=False)
#     print_success("Finetune data generated.")
    
    
# def main():
#     generate_finetune_data("/home/s448780/workspace/synkrasis_master/logs/mbpp_gpt_3_5.txt")
    
    
# if __name__ == "__main__":
#     # Generate finetune data
#     main()
    
#     # # Apply dataset formatting function
#     # dataset = load_dataset(path = "csv", data_files = "services/Finetune/mbpp_finetune_data.csv")
#     # dataset = dataset.map(formatting_func, batched = True)
#     # print(dataset["train"]["text"][0])