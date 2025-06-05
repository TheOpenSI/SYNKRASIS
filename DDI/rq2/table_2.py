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

data = results.copy()

all_fs_keys = set()
for model_data in data.values():
    all_fs_keys.update(model_data.keys())
fs_columns = ['fs_0'] + sorted(all_fs_keys - {'fs_0'})

# Start building the LaTeX table
latex_table = """\\begin{table}[!h]
    \\label{tab:model_performance}
    \\centering
    \\begin{tabular}{l""" + "c" * len(fs_columns) + """}
        \\hline
        \\textbf{Model}"""

# Add column headers
for fs_key in fs_columns:
    latex_table += f" & \\textbf{{{fs_key}}}"
latex_table += " \\\\\n        \\hline\n"

# Add data rows
for model_name in sorted(data.keys()):
    # Clean up model name for LaTeX (escape underscores, etc.)
    clean_model_name = model_name.replace("_", "\\_").replace(":", ":")
    latex_table += f"        {clean_model_name}"
    
    # Add values for each column, or "-" if not present
    for fs_key in fs_columns:
        if fs_key in data[model_name]:
            value = data[model_name][fs_key]
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