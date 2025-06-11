import json
import matplotlib.pyplot as plt

mistral = ["ddi_results/mistral:instruct_humaneval_DDI.json",
           "ddi_results_fs/mistral:instruct_humaneval_DDI_fs2.json",
           "ddi_results_fs/mistral:instruct_humaneval_DDI_fs4.json"]
deepseek = ["ddi_results/deepseek-coder-v2:16b_humaneval_DDI.json",
            "ddi_results_fs/deepseek-coder-v2:16b_humaneval_DDI_fs1.json",
            "ddi_results_fs/deepseek-coder-v2:16b_humaneval_DDI_fs2.json"]
devstral = ["ddi_results/devstral:24b_humaneval_DDI.json",
            "ddi_results_fs/devstral:24b_humaneval_DDI_fs2.json",
            "ddi_results_fs/devstral:24b_humaneval_DDI_fs3.json"]
qwen = ["ddi_results/qwen2.5-coder_humaneval_DDI.json",
        "ddi_results_fs/qwen2.5-coder_humaneval_DDI_fs2.json",
        "ddi_results_fs/qwen2.5-coder_humaneval_DDI_fs4.json"]

colours = ["red", "blue", "green", "purple"]

def get_model_name(model: str) -> str:
    if "mistral" in model:
        return "Mistral:Instruct:7b"
    elif "deepseek" in model:
        return "DeepSeek-Coder-V2:16b"
    elif "devstral" in model:
        return "Devstral:24b"
    elif "qwen" in model:
        return "Qwen2.5-Coder:7b"

vals = [0, 50, 80]
counter = 1

fig, axes = plt.subplots(2, 2, figsize=(12, 8))

for model, colour in zip([mistral, deepseek, devstral, qwen], colours):
    plt.subplot(2, 2, counter)
    for i, file in enumerate(model):
        with open(file, "r") as f:
            data = json.load(f)
            plt.plot(data["normalised_effectiveness"].keys(),
                     data["normalised_effectiveness"].values(),
                     color=colour,
                     linestyle="solid" if i == 0 else "--" if i == 1 else "dotted",
                     linewidth=1,
                     label=f"{get_model_name(file)} - A_{vals[i]}")
    
    plt.legend(loc='upper right', fontsize=8, frameon=False)
    plt.title(get_model_name(model[0]))
    counter += 1

fig.supxlabel('Attempt', fontsize=14)
fig.supylabel('Normalised Effectiveness', fontsize=14)

plt.tight_layout()
plt.savefig("DDI/rq2/fig_2.png", dpi=300)