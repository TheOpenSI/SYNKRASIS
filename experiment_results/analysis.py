import pandas as pd
import matplotlib.pyplot as plt

df_span = pd.read_csv("/home/s448780/workspace_hcc4/SYNKRASIS/experiment_results/qwen2.5-coder_HumanEval_results_debug_span.csv")
df_pass = pd.read_csv("/home/s448780/workspace_hcc4/SYNKRASIS/experiment_results/qwen2.5-coder_HumanEval_results_pass@5.csv")
df_pc = pd.read_csv("/home/s448780/workspace_hcc4/SYNKRASIS/experiment_results/qwen2.5-coder_HumanEval_results_pycapsule.csv")


def effectiveness(df: pd.DataFrame) -> list[float]:
    # Attempt reach
    total = len(df)
    attempt_count = df["fix_mode_attempt_count"].value_counts().sort_index()
    denom = total - attempt_count.cumsum().shift(fill_value=0)
    # Success
    success = df[df["status"] == "pass"]["fix_mode_attempt_count"].value_counts().sort_index()
    # Effectiveness
    effectiveness = []
    for attempt in range(6):
        effectiveness.append(success.get(attempt, 0) / denom[attempt] * 100)
    
    return effectiveness
    
data = {    
        "pass@n": df_pass,
        "pycapsule": df_pc,
        "debug_span" : df_span
       }

result = []
   
for name, df in data.items():
    success_rate = df["status"].value_counts(normalize = True) * 100
    effectiveness(df)
    result.append({
        "gen_type": name,
        "success_rate": success_rate,
        "effectiveness": effectiveness(df)
    })

print(result)

# Plotting
fig, ax = plt.subplots(1, 2, figsize=(15, 5))
for res in result:
    ax[0].plot(res["effectiveness"], label=res["gen_type"])
    ax[1].bar(res["gen_type"], res["success_rate"]["pass"], label=res["gen_type"])
    ax[1].text(res["gen_type"], res["success_rate"]["pass"] + 1, f'{res["success_rate"]["pass"]:.1f}', ha='center', fontsize=10)

ax[0].set_title("Effectiveness")
ax[0].set_xlabel("Normalised Effectiveness")
ax[0].set_ylabel("Success Rate (%)")

ax[1].set_title("Success Rate")
ax[1].set_xlabel("Code Generation Type")
ax[1].set_ylabel("Percentage (%)")
ax[1].legend(bbox_to_anchor=(1, 1))

plt.savefig("/home/s448780/workspace_hcc4/SYNKRASIS/experiment_results/humaneval_results.png")