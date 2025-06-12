import re
import warnings
from transformers import AutoTokenizer

# Suppress the sequence length warning since we only need tokenization
warnings.filterwarnings("ignore", message="Token indices sequence length is longer than the specified maximum sequence length")

def count_tokens_rq3(file_path):
    """Count tokens for RQ3 combined logs"""
    # Model patterns and their corresponding tokenizer names
    model_configs = {
        "[MISTRAL:INSTRUCT]": "mistralai/Mistral-7B-Instruct-v0.2",
        "[DEEPSEEK-CODER-V2:16B]": "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct",
        "[CODESTRAL:22B]": "mistralai/Codestral-22B-v0.1"
    }
    
    # Escape brackets for regex
    model_patterns = {}
    tokenizers = {}
    
    for model_name, tokenizer_name in model_configs.items():
        escaped_pattern = model_name.replace("[", r"\[").replace("]", r"\]")
        model_patterns[model_name] = escaped_pattern
        
        try:
            tokenizers[model_name] = AutoTokenizer.from_pretrained(tokenizer_name)
        except Exception as e:
            print(f"Warning: Could not load tokenizer for {model_name}: {e}")
            tokenizers[model_name] = None
    
    # Read the log file
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Extract and count tokens for each model
    results = {}
    
    for model_name, pattern in model_patterns.items():
        # Capture ALL occurrences, including those not followed by ========== 
        regex_pattern = rf"{pattern}(.*?)(?=(?:\[(?:MISTRAL:INSTRUCT|DEEPSEEK-CODER-V2:16B|CODESTRAL:22B)\]|=={{10}}|$))"
        matches = re.findall(regex_pattern, content, re.DOTALL)
        
        if matches:
            # Join all matches for this model
            model_content = "\n".join(matches)
            
            # Count tokens using the model's tokenizer
            if tokenizers[model_name] is not None:
                output_text = extract_output_text(model_content)
                tokens = len(tokenizers[model_name].encode(output_text))
            else:
                tokens = 0
            
            results[model_name] = {
                'sections': len(matches),
                'output_tokens': tokens
            }
        else:
            results[model_name] = {
                'sections': 0,
                'output_tokens': 0
            }
    
    return results

def count_tokens_continuous(file_path, model_name, tokenizer_name):
    """Count tokens for continuous logs (single model per file)"""
    try:
        tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
    except Exception as e:
        print(f"Warning: Could not load tokenizer for {model_name}: {e}")
        return 0
    
    # Read the log file
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Extract output text and count tokens
    output_text = extract_output_text(content)
    tokens = len(tokenizer.encode(output_text))
    
    return tokens

def extract_output_text(content):
    """
    Extract only the model output text from the log content.
    Based on the format: START -> [MODEL] -> response -> END
    """
    # Pattern to extract content between START and END markers
    start_end_pattern = r"START.*?\[(?:MISTRAL:INSTRUCT|DEEPSEEK-CODER-V2:16B|CODESTRAL:22B)\].*?\[0m\s*(.*?)(?:={40,}.*?END|$)"
    
    matches = re.findall(start_end_pattern, content, re.DOTALL)
    
    if matches:
        return "\n".join(matches)
    
    # Fallback: if no START/END structure, return all content
    return content

# Main execution
if __name__ == "__main__":
    print("TOKEN USAGE BY MODEL:")
    print("-" * 50)
    
    # RQ3 combined logs
    rq3_file = "logs/he_mistral_devstral_deepcode_codestral_50_80.txt"
    try:
        rq3_results = count_tokens_rq3(rq3_file)
        print("\nRQ3 Results:")
        for model_name, data in rq3_results.items():
            clean_name = model_name.replace("[", "").replace("]", "")
            print(f"  {clean_name}: {data['output_tokens']:,} tokens ({data['sections']} sections)")
    except FileNotFoundError:
        print(f"RQ3 file not found: {rq3_file}")
    
    # Continuous logs
    continuous_files = [
        ("logs/he_deepseek_coder_v2_16b.txt", 
         "DeepSeek-Coder-V2-16B", 
         "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct"),
        
        ("logs/he_codestral.txt", 
         "Codestral-22B", 
         "mistralai/Codestral-22B-v0.1"),
        
        ("logs/he_mistral-instruct_7b.txt", 
         "Mistral-Instruct-7B", 
         "mistralai/Mistral-7B-Instruct-v0.2")
    ]
    
    print("\nContinuous Results:")
    for file_path, model_name, tokenizer_name in continuous_files:
        try:
            tokens = count_tokens_continuous(file_path, model_name, tokenizer_name)
            print(f"  {model_name}: {tokens:,} tokens")
        except FileNotFoundError:
            print(f"  {model_name}: File not found - {file_path}")
        except Exception as e:
            print(f"  {model_name}: Error - {e}")


# import pandas as pd

# fss = [
#     "experiment_results/mistral:instruct_HumanEval_results.csv",
#     "experiment_results_fs/mistral:instruct_HumanEval_results_fs2.csv",
#     "experiment_results_fs/mistral:instruct_HumanEval_results_fs4.csv",
#     "experiment_results/deepseek-coder-v2:16b_HumanEval_results.csv",
#     "experiment_results_fs/deepseek-coder-v2:16b_HumanEval_results_fs1.csv",
#     "experiment_results_fs/deepseek-coder-v2:16b_HumanEval_results_fs2.csv",
#     "experiment_results/codestral:22b_HumanEval_results.csv",
#     "experiment_results_fs/codestral:22b_HumanEval_results_fs3.csv",
#     "experiment_results_fs/codestral:22b_HumanEval_results_fs5.csv"
# ]

# for i, fs in enumerate(fss):
#     if i%3 == 0:
#         print("="*50)
#     df = pd.read_csv(fs)
#     print(fs)
#     total_attempts = df["fix_mode_attempt_count"].sum() + len(df)
#     print(f"Total attempts: {total_attempts}")