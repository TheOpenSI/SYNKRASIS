import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

from code_security.graphs.WeaknessCWEGraph import WeaknessCWEGraph
from code_security.AlphaMultiRun import ALPHAMultiRun
from code_security.ALPHA import ALPHA

EDA_PATH = "code_security/eda_results.json"

graph = WeaknessCWEGraph(EDA_PATH)

# Create ALPHA multi-run analyser
# alpha = ALPHAMultiRun(graph)

# SecurityEval
# e_1 = ("services/CodeSecurity/experiments/exp_dir_SecurityEval_1/SecurityEval_qwen2_5_coder_32b_"
#     "mistral_latest_qwen2_5_coder_latest_llama3_1_latest_"
#     "phi4_latest_deepseek_coder_6_7b_devstral_24b.json")
# e_2 = ("services/CodeSecurity/experiments/exp_dir_SecurityEval_2/SecurityEval_qwen2_5_coder_32b_"
#     "mistral_latest_qwen2_5_coder_latest_llama3_1_latest_"
#     "phi4_latest_deepseek_coder_6_7b_devstral_24b.json")
# e_3 = ("services/CodeSecurity/experiments/exp_dir_SecurityEval_3/SecurityEval_qwen2_5_coder_32b_"
#     "mistral_latest_qwen2_5_coder_latest_llama3_1_latest_"
#     "phi4_latest_deepseek_coder_6_7b_devstral_24b.json")

# SVEN
e_1 = ("services/CodeSecurity/experiments/exp_dir_SVEN_python_1/SVEN_python_qwen2_5_coder_32b_"
    "python_mistral_latest_python_qwen2_5_coder_latest_python_llama3_1_latest_"
    "python_phi4_latest_python_deepseek_coder_6_7b_python_devstral_24b.json")
e_2 = ("services/CodeSecurity/experiments/exp_dir_SVEN_python_2/SVEN_python_qwen2_5_coder_32b_"
    "python_mistral_latest_python_qwen2_5_coder_latest_python_llama3_1_latest_"
    "python_phi4_latest_python_deepseek_coder_6_7b_python_devstral_24b.json")
e_3 = ("services/CodeSecurity/experiments/exp_dir_SVEN_python_3/SVEN_python_qwen2_5_coder_32b_"
    "python_mistral_latest_python_qwen2_5_coder_latest_python_llama3_1_latest_"
    "python_phi4_latest_python_deepseek_coder_6_7b_python_devstral_24b.json")

# summary = alpha.get_alpha_multi_run(
#     prediction_paths=[
#         e_1,
#         e_2,
#         e_3
#     ],
#     gt_cwe_extraction_function=lambda x: str(int(x.split('-')[-1])),
#     output_dir='code_security/alpha_results/sven_multi_run'
# )

# SAST
sven = "services/CodeSecurity/experiments/SAST/SVEN_sast_transformed_confidence.json"
security_eval = "services/CodeSecurity/experiments/SAST/SecurityEval_sast_transformed_confidence.json"

alpha_instance = ALPHA(
    # predictions_path=sven,
    predictions_path=security_eval,
    eda_path=EDA_PATH
)
alpha_instance.export_alpha(
    output_path="code_security/alpha_results/sast_security_eval/sast_security_eval.json"
)