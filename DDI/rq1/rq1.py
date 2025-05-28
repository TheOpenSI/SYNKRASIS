import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import json
from pathlib import Path

from utils.output_message_format.output_colour import print_error, print_success

def extract_model_dataset(filename: str) -> tuple:
    """
    Extract model name and dataset name from filename.
    
    Format: model_dataset_results_extra.csv
    Examples:
    - gpt-3.5-turbo_humaneval_results_e1.csv -> ('gpt-3.5-turbo', 'humaneval')
    
    Args:
        filename (str): CSV filename
        
    Returns:
        tuple: (model_name, dataset_name)
    """
    name = filename.replace('.csv', '')
    
    # Split by underscore
    parts = name.split('_')
    
    # Ensure we have at least model and dataset parts
    if len(parts) < 2:
        print_error(f"Invalid filename format: {filename}")
        return None, None
    
    # First part is always model
    model = parts[0]
    
    # Find where 'results' appears (if it does)
    try:
        results_idx = next(i for i, part in enumerate(parts) if 'results' in part.lower())
        # Dataset is everything between model and results
        dataset_parts = parts[1:results_idx]
    except StopIteration:
        # No 'results' found, assume last part might be extra info
        # Take everything except first and last part
        dataset_parts = parts[1:-1] if len(parts) > 2 else parts[1:]
    
    dataset = '_'.join(dataset_parts) if dataset_parts else 'unknown'
    
    return model, dataset


def calculate_normalised_influence(file_path: str) -> dict:
    """
    Calculate normalized debugging influence following the formula in pycapsule:
    I_i = S_i / N_i, where N_i = N - Σ(j=0 to i-1) S_j
    
    Args:
        file_path (str): Path to CSV file
        
    Returns:
        dict: Contains influence metrics for each attempt
    """
    try:
        df = pd.read_csv(file_path)
        
        # Get successful attempts counts by attempt number
        pass_counts = \
            df[df["status"] == "pass"]["fix_mode_attempt_count"].value_counts().sort_index()
        
        # Total number of problems
        N = len(df)
        
        if N == 0:
            return {'influences': {}, 'total_problems': 0}
        
        # Calculate S_i (number of problems solved at attempt i) for each attempt
        S = {}
        for attempt in range(6):  # 0 to 5 attempts
            S[attempt] = pass_counts.get(attempt, 0)
        
        # Calculate normalized influence I_i for each attempt
        influences = {}
        cumulative_solved = 0  # This tracks Σ(j=0 to i-1) S_j
        
        for i in range(6):  # 0 to 5 attempts
            # N_i = N - Σ(j=0 to i-1) S_j (problems remaining before attempt i)
            N_i = N - cumulative_solved
            
            # S_i = number of problems solved at attempt i
            S_i = S[i]
            
            # I_i = S_i / N_i (normalized influence of attempt i)
            if N_i > 0:
                I_i = S_i / N_i
            else:
                I_i = 0.0
            
            influences[i] = I_i
            
            # Update cumulative count for next iteration
            cumulative_solved += S_i
        
        return {
            'influences': influences,
            'total_problems': N,
            'problems_solved_by_attempt': dict(S),
            'total_solved': cumulative_solved
        }
        
    except Exception as e:
        print_error(f"Error processing {file_path}: {e}")
        return {'influences': {}, 'total_problems': 0}


def analyse_all_files(directory_path):
    """
    Analyse all CSV files in directory and return structured results.
    
    Args:
        directory_path (str): Directory containing CSV files
        
    Returns:
        dict: {model_name: {dataset_name: influence_data}}
        where influence_data contains the normalized influence for each attempt
    """
    results = {}
    csv_files = [f for f in os.listdir(directory_path) if f.endswith('.csv')]
    
    for csv_file in csv_files:
        file_path = os.path.join(directory_path, csv_file)
        
        # Extract model and dataset names
        model, dataset = extract_model_dataset(csv_file)
        
        if model is None or dataset is None:
            print_error(f"Could not parse filename: {csv_file}")
            continue
        
        # Calculate normalized influence
        influence_data = calculate_normalised_influence(file_path)
        
        # Store in nested dict structure
        if model not in results:
            results[model] = {}
        
        results[model].setdefault(dataset, []).append(influence_data)
        
        print_success (f"Processed: {csv_file} -> {model}/{dataset}")
    
    return results
                                  

def print_results_summary(results):
    """
    Print a detailed summary of the normalized influence results.
    
    Args:
        results (dict): Results dictionary from analyse_all_files
    """
    print("\nNORMALIZED DEBUGGING INFLUENCE ANALYSIS")
    print("=" * 60)
    
    for model, datasets in results.items():
        print(f"\nModel: {model}")
        print("-" * 40)
        
        for dataset, data in datasets.items():
            print(f"\n  Dataset: {dataset}")
            print(f"  Total Problems: {data['total_problems']}")
            print(f"  Total Solved: {data['total_solved']}")
            
            if data['total_problems'] > 0:
                success_rate = data['total_solved'] / data['total_problems']
                print(f"  Overall Success Rate: {success_rate:.4f} ({success_rate*100:.2f}%)")
            
            print(f"  Normalized Influence by Attempt:")
            influences = data['influences']
            problems_by_attempt = data['problems_solved_by_attempt']
            
            cumulative = 0
            for attempt in range(6):
                if attempt in influences and influences[attempt] > 0:
                    remaining = data['total_problems'] - cumulative
                    solved = problems_by_attempt.get(attempt, 0)
                    influence = influences[attempt]
                    
                    print(f"    Attempt {attempt}: {solved}/{remaining} \
                        = {influence:.4f} ({influence*100:.2f}%)")
                    cumulative += solved
    
    print("\n" + "=" * 60)


def get_influence_by_attempt(results, model, dataset, attempt):
    """
    Helper function to get specific influence value.
    
    Args:
        results (dict): Results from analyse_all_files
        model (str): Model name
        dataset (str): Dataset name  
        attempt (int): Attempt number (0-5)
        
    Returns:
        float: Normalized influence I_i for the specified attempt
    """
    try:
        return results[model][dataset]['influences'][attempt]
    except KeyError:
        return 0.0
    

def get_average_influence(results:dict) -> list[dict[str, list[dict[str, list[float]]]]]:
    """
    Calculate average normalised influence across all models and datasets.

    Args:
        results (dict): Results from analyse_all_files, structured as:
        {
            model_name: {
                dataset_name: [influence_data]
            }
        }
    Returns:
        list[dict[str, list[dict[str, list[float]]]]]: Normalised influence averages
    """
    result = []
    # Model
    for model in results.keys():
        model_effectiveness = {"model": model, "effectiveness": []}
        # Dataset
        for dataset in results[model].keys():
            # Experiments
            dataset_effectiveness = {"dataset": dataset, "effectiveness": []}
            effectiveness = []
            for expriment in results[model][dataset]: # dataset is a list
                effectiveness.append(expriment["influences"].values())
            
            # Average
            # zip(*effectiveness) transposes the list
            average_effectiveness = \
                [round((sum(col) / len(col)) * 100, 3) \
                    for col in zip(*effectiveness)]
            average_effectiveness = average_effectiveness[1:]  # Remove first element (attempt 0)
            dataset_effectiveness["effectiveness"] = average_effectiveness
            model_effectiveness["effectiveness"].append(dataset_effectiveness)
        result.append(model_effectiveness)
    return result          
                
                
if __name__ == "__main__":
    # testing parsing
    test_files = [
        "gpt-3.5-turbo_humaneval_results_e1.csv",
        "claude_humaneval_et_python_results_v2.csv", 
        "gpt-4_mbpp_results_1.csv",
        "qwen2.5-coder_bigcodebench_results_c2_a1.csv"
    ]
    
    print("Testing parsing:")
    for filename in test_files:
        model, dataset = extract_model_dataset(filename)
        print(f"{filename} -> Model: '{model}', Dataset: '{dataset}'")
    
    # nomralisation
    results = analyse_all_files("experiment_results")
    data = get_average_influence(results)
    with open("DDI/data/norm_effect_data_wo_attempt_0.json", "w") as f:
        json.dump(data, f, indent=2)
    print_success("Normalised influence data saved to DDI/data/norm_effect_data.json")