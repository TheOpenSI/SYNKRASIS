import os
import json
# from services.DDI.DDI import DDI

# result_dir = "experiment_results"

# files = []
# for f in os.listdir(result_dir):
#     if "humaneval" in f.lower():
#         if "et" not in f.lower():
#             files.append(f)

# for f in files:
#     print(f"Running DDI for {f}")
#     model_name = f.split("_")[0]
#     ddi = DDI(file_path=os.path.join(result_dir, f), 
#               model_name=model_name,
#               maximum_debugging_attempts=5,
#               dataset="humaneval")
#     ddi()

latex_table = """
\\begin{table}[!h]
    \label{tab: ddi_results}
    \centering
    \\begin{tabular}{p{4.2cm}p{1cm}p{1cm}p{0.8cm}p{2.2cm}p{1cm}}
        \hline
        \\textbf{Model} & $E_0$ & \\textbf{$\lambda$} & \\textbf{$A_\phi$} & \\textbf{$t_\\theta$} & $R^2$\\\\
        \hline
""".strip() + "\n"

ddi_files = []
for f in os.listdir("ddi_results"):
    if f.endswith(".json"):
        ddi_files.append(f)

model_data = {}

for f in ddi_files:
    model_name = f.split("_")[0]
    
    if model_name in model_data:
        continue
        
    with open(os.path.join("ddi_results", f), "r") as file:
        data = json.load(file)
        
        model_data[model_name] = {
            "E_0": data["E_0"],
            "lambda": data["lambda"], 
            "A_phi": data["A_phi"],
            "t_theta_ceiling": data["t_theta_ceiling"],
            "fit_quality": data["fit_quality"][0].upper() + data["fit_quality"][1:]
        }

for model_name in sorted(model_data.keys()):
    data = model_data[model_name]
    try:
        latex_table += "\t" + f"""
        \\textbf{{{model_name}}} & {data["E_0"]:.3f} & {data["lambda"]:.4f} & {data["A_phi"]:.3f} & {data["t_theta_ceiling"]} & {data["fit_quality"]}\\\\
        """.strip() + "\n"
    except TypeError:
        latex_table += "\t" + f"""
        \\textbf{{{model_name}}} & {data["E_0"]} & {data["lambda"]} & {data["A_phi"]} & {data["t_theta_ceiling"]} & {data["fit_quality"]} \\\\
        """.strip() + "\n"

latex_table += "\t" + """
\hline
\\end{tabular}
\caption{DDI Results for Different Models for $\\theta \in 50, 80, 90, 95, 99$ on the HumanEval dataset}
\end{table}
""".strip()

print(latex_table)