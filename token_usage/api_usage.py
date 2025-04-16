import os
import re
import tiktoken
import pandas as pd
from tqdm import tqdm
from transformers import AutoTokenizer

df = pd.DataFrame(columns=["Model", "Dataset", "Experiment", "Tokens", "Average_attempt_count"])
hf_tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-Coder-7B-Instruct")
openai_tokenizer = tiktoken.get_encoding("cl100k_base")

def count_tokens(text: str, is_openai: bool) -> int:
    tokenizer = openai_tokenizer if is_openai else hf_tokenizer
    tokens = tokenizer.encode(text)
    return len(tokens)


# Model specicific regex
def get_regex_pattern(model_name: str,
                      models: dict) -> str:
    target_model_name = models.get(model_name).replace(".", "\.")
    return (rf"(?<={target_model_name}]\[0m)"
            r"(.*?)"
            r"(?=(\[SUCCESS\]\[0m Container found)|"
            r"[=]{10,}|"
            r"(\[WARNING\]\[0m Container does not exist))")

def get_file_paths():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    model_names = {"gpt4": "GPT-4-1106-PREVIEW", 
                   "gpt35": "GPT-3.5-TURBO-1106", 
                   "qwen": "QWEN2.5-CODER"}
    log_files = {}
    csv_files = {}
    sub_1_dirs = [sub_1
                  for sub_1 in os.listdir(root_dir) 
                  if not (sub_1.endswith(".py") or sub_1.endswith(".txt") or sub_1.endswith(".csv"))]
    
    for sub_1_dir in sub_1_dirs:
        # Dataset level
        sub_2_dirs = [sub_2
                    for sub_2 in os.listdir(os.path.join(root_dir, sub_1_dir))]
        
        # Experiment level
        for sub_2_dir in sub_2_dirs:
            sub_3_dirs = [sub_3
                        for sub_3 in os.listdir(os.path.join(root_dir, sub_1_dir, sub_2_dir))]
            
            # Log level
            for sub_3_dir in sub_3_dirs:
                log_file = os.listdir(
                    os.path.join(root_dir, sub_1_dir, sub_2_dir, sub_3_dir)
                )
                txt_file = ""
                csv_file = ""
                for file in log_file:
                    if file.endswith(".txt"):
                        txt_file = file
                    elif file.endswith(".csv"):
                        csv_file = file
                if txt_file == "":
                    continue
                else:
                    log_files.setdefault(sub_1_dir, []).append(os.path.join(root_dir,
                                                                            sub_1_dir, 
                                                                            sub_2_dir, 
                                                                            sub_3_dir,
                                                                            txt_file))
                    df = pd.read_csv(os.path.join(root_dir,
                                                  sub_1_dir, 
                                                  sub_2_dir, 
                                                  sub_3_dir,
                                                  csv_file))
                    average_attemet_count = (df["fix_mode_attempt_count"].sum() + len(df))/len(df)
                    csv_files.setdefault(sub_1_dir, []).append(average_attemet_count)
                    
                    
    return log_files, csv_files, model_names
        

def run_api_usage():
    file_paths, attempt_counts, model_names_dict = get_file_paths()
    for item in file_paths.items():
        # print(item[0])
        model = item[0]
        attempt_counts_list = attempt_counts.get(model)
        regex_pattern = get_regex_pattern(model, model_names_dict)
        
        for file, count in zip(item[1], attempt_counts_list):
            # print(f"\t{file}")
            token_count = 0
            with open(file, "r") as f:
                log = f.read()
                inferences = re.findall(regex_pattern,
                                       log,
                                       re.DOTALL)
                # print(len(inferences))
                # if len(inferences) == 0:
                #     print(f"Could not extract inference from - {file}")
                is_openai = False if model == "qwen" else True
                for inference in tqdm(inferences):
                    target = [t for t in inference if t][0] # Because i have 3 capturing groups
                    number_of_tokens = count_tokens(target, is_openai)
                    token_count += number_of_tokens
                row = {"Model": model, 
                       "Dataset": file.split("/")[-3],
                       "Experiment": file.split("/")[-2],
                       "Tokens": token_count,
                       "Average_attempt_count": count}
                df.loc[len(df)] = row
                # print(f"Total tokens in {file}: {token_count}")
    df.to_csv("token_usage/token_usage.csv", index=False)
    

if __name__ == "__main__":
    run_api_usage()