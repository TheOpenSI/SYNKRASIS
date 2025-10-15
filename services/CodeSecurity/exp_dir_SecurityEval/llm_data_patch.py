import json
import re
from tqdm import tqdm

# Original w/o summary analysis
DATA_PATH = ("/home/s448780/workspace_hcc4/SYNKRASIS/services/"
             "CodeSecurity/exp_dir_SecurityEval/"
             "SecurityEval_qwen2_5_coder_32b_mistral_latest_qwen2_5_coder_latest_llama3_1_latest.json")

with open(DATA_PATH, 'r') as f:
    data_org = json.load(f)

# After adding summary analysis
DATA_PATH_SUM = ("/home/s448780/workspace_hcc4/SYNKRASIS/services/"
             "CodeSecurity/exp_dir_SecurityEval/"
             "SecurityEval_qwen2_5_coder_32b_mistral_latest_qwen2_5_coder_latest_llama3_1_latest_summary.json")

with open(DATA_PATH_SUM, 'r') as f:
    data_sum = json.load(f)


def count_cwe_in_summary(summary: str) -> int:
    cwe_pattern = r'CWE[\s]?-[\s]?\d+'
    cwes = re.findall(cwe_pattern, summary, re.IGNORECASE)
    cwes = set(cwes)
    return len(cwes)


def get_cwe_from_summary(summary: str) -> list:
    cwe_pattern = r'CWE[\s]?-[\s]?\d+'
    cwes = re.findall(cwe_pattern, summary, re.IGNORECASE)
    cwes = set(cwes)
    return list(cwes)


def extract_summary_from_response(response: str) -> str:
    summary_match = re.search(r'Findings*\sSummary:*\s*([\s\S]*)', response, re.DOTALL)
    if summary_match:
        return summary_match.group(1).strip()
    else:
        return ""
    
if __name__ == "__main__":
    for dataset, label in [(data_org, "W/O Summary Analysis"), 
                           (data_sum, "With Summary Analysis")]:
        print(f"Processing: {label}")
        summary_missing_count = {}
        mismatch_count = {}
        for sample_entry in tqdm(dataset):
            analysis: list[dict] = sample_entry['analysis']
            print(f"Sample ID: {sample_entry['sample_index']}")
            for llm_entry in analysis:
                model_name: str = llm_entry['llm_model']
                summary: str = llm_entry['parsed_response']['raw_summary']
                raw_response: str = llm_entry['raw_response']
                cwe: list = llm_entry['parsed_response']['cwe']
                
                new_summary = extract_summary_from_response(raw_response)
                new_cwe_from_summary = get_cwe_from_summary(new_summary)
                new_cwe_from_response = get_cwe_from_summary(raw_response)
                
                is_summary_missing = summary.strip() == ""
                is_new_summary_missing = new_summary.strip() == ""
                is_summary_same_as_new = summary.strip() == new_summary.strip()
                does_cwe_match_w_summary = set(cwe) == set(new_cwe_from_summary)
                does_cwe_match_w_response = set(cwe) == set(new_cwe_from_response)
                does_cwe_match_w_new_summary = set(new_cwe_from_summary) == set(new_cwe_from_response)
                old_cwe_count = len(cwe)
                cwe_count_from_new_summary = len(new_cwe_from_summary)
                cwe_count_from_response = len(new_cwe_from_response)
                
                if not all([is_summary_missing, is_new_summary_missing, is_summary_same_as_new,
                            does_cwe_match_w_summary, does_cwe_match_w_response,
                            does_cwe_match_w_new_summary]):
                    print((f"{model_name}: sum_miss={is_summary_missing}, |"
                        f"new_sum_miss={is_new_summary_missing}, |"
                        f"summary_same={is_summary_same_as_new}, |"
                        f"cwe_match_w_summary={does_cwe_match_w_summary}, |"
                        f"cwe_match_w_response={does_cwe_match_w_response}, |"
                        f"cwe_match_w_new_summary={does_cwe_match_w_new_summary} |"
                        f"old_cwe_count={old_cwe_count}, |"
                        f"cwe_count_from_new_summary={cwe_count_from_new_summary}, |"
                        f"cwe_count_from_response={cwe_count_from_response}"))
                
                # summary missing
                if is_summary_missing:
                    summary_missing_count.setdefault(model_name, 0)
                    summary_missing_count[model_name] += 1

                # update
                # llm_entry['parsed_response']['raw_summary'] = summary
                # llm_entry['parsed_response']['cwe'] = get_cwe_from_summary(summary)

        print("-" * 40)
        print("Summary missing:")
        for model, cnt in summary_missing_count.items():
            print(f"{model}: {cnt} missing summaries")