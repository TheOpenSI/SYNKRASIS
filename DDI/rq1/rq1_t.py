import numpy as np

# calculate_t_theta
t_theta = lambda theta, lambda_val : np.log(100/(100-theta))/ lambda_val

# threshold
theta_vals = [50, 80, 90, 95, 99]
# lambda
lambda_gpt_3_5 = 0.7061
lambda_gpt_4 = 0.5484
lambda_qwen = 0.5003
# models
models = ["GPT-3.5-Turbo-1106", "GPT-4-1106-Preview", "Qwen2.5-Coder-7B-Instruct"]

# latex table
top = """
\\begin{table}[!h]
    \centering
    \\begin{tabular}{ccc}
        \hline
        \\textbf{$\\theta$ (\%)} & Equation~\\ref{eq:ttheta_formula} Outcome & \\textbf{$\\theta$ at Attempt} \\
        \hline
""".strip() + "\n"

for lambda_val, model in zip([lambda_gpt_3_5, lambda_gpt_4, lambda_qwen], models):
    # print(f"λ = {lambda_val}")
    # print("=" * 30)
    top += "\t\multicolumn{3}{c}{" + model + ", $\lambda$ = "+ str(lambda_val) + "} \\\\\n"
    for theta in theta_vals:
        t = t_theta(theta, lambda_val)
        t_ceiling = int(np.ceil(t))
        # print(f"t(θ={theta}) = {t:.4f} (λ = {lambda_val}), attempt = {t_ceiling}")
        top += f"\t\quad {theta} & {t:.4f} & {t_ceiling} \\\\\n"
    top += "\t\hline\n\n"

top += """
\end{tabular}
\end{table}
""".strip()

print(top)