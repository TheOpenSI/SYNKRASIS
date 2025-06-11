import os
import json

results = {}
fs_files = os.listdir("ddi_results_fs")
norm_files = os.listdir("ddi_results")

for fs_file in fs_files:
    if fs_file.endswith(".json"):
        meta_data = fs_file.split("_")
        model_name = meta_data[0]
        fs = meta_data[-1].split(".")[0]
        
        with open(f"ddi_results_fs/{fs_file}", "r") as f:
            fs_data = json.load(f)
            acc = fs_data["A_phi"]
            results.setdefault(model_name, {})[fs] = acc

for norm_file in norm_files:
    if norm_file.endswith(".json"):
        meta_data = norm_file.split("_")
        model_name = meta_data[0]
        fs = "fs_0"
        
        with open(f"ddi_results/{norm_file}", "r") as f:
            fs_data = json.load(f)
            acc = fs_data["A_phi"]
            if model_name in results.keys():
                results[model_name][fs] = acc
                
print(results)

data = results.copy()
all_fs_keys = set()
for model_data in data.values():
    all_fs_keys.update(model_data.keys())

# Reorganize data into 3 columns: A_0, A_50, A_80
reorganized_data = {}
for model_name, model_data in data.items():
    reorganized_data[model_name] = {}
    
    # A_0 comes from fs_0
    if 'fs_0' in model_data:
        reorganized_data[model_name]['A_0'] = model_data['fs_0']
    
    # Get all non-fs_0 keys and sort them by number
    other_keys = [k for k in model_data.keys() if k != 'fs_0']
    other_keys.sort(key=lambda x: int(x.split('_')[1]) if '_' in x else int(x[2:]))
    
    # Assign the two non-fs_0 values to A_50 and A_80
    if len(other_keys) >= 1:
        reorganized_data[model_name]['A_{50}'] = model_data[other_keys[0]]
    if len(other_keys) >= 2:
        reorganized_data[model_name]['A_{80}'] = model_data[other_keys[1]]

# Define the 3 columns
columns = ['A_0', 'A_{50}', 'A_{80}']

# Start building the LaTeX table
latex_table = """\\begin{table}[!h]
    \\label{tab:model_performance}
    \\centering
    \\begin{tabular}{l""" + "c" * len(columns) + """}
        \\hline
        \\textbf{Model}"""

# Add column headers
for col in columns:
    latex_table += f" & \\textbf{{{col}}}"
latex_table += " \\\\\n        \\hline\n"

# Add data rows
for model_name in sorted(reorganized_data.keys()):
    # Clean up model name for LaTeX (escape underscores, etc.)
    clean_model_name = model_name.replace("_", "\\_").replace(":", ":")
    latex_table += f"        {clean_model_name}"
    
    # Add values for each column, or "-" if not present
    for col in columns:
        if col in reorganized_data[model_name]:
            value = reorganized_data[model_name][col]
            latex_table += f" & {value:.4f}"
        else:
            latex_table += " & -"
    latex_table += " \\\\\n"

# Close the table
latex_table += """        \\hline
    \\end{tabular}
    \\caption{Model Performance Results}
\\end{table}"""

print(latex_table)