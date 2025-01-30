import os
import pandas as pd

def calculate_mean_fix_attempts(folder_path):
    for file_name in os.listdir(folder_path):
        if file_name.endswith(".csv"):  # only CSV files
            file_path = os.path.join(folder_path, file_name)
            
            try:
                df = pd.read_csv(file_path)
                
                if 'fix_mode_attempt_count' in df.columns:
                    mean_value = (df['fix_mode_attempt_count'].sum() + len(df))/ len(df)
                    print(f"{file_name}: {mean_value:.2f}")
                else:
                    print(f"{file_name}: Column 'fix_mode_attempt_count' not found.")
            except Exception as e:
                print(f"Error processing {file_name}: {e}")


folder_path = "experiment_results/"
calculate_mean_fix_attempts(folder_path)
