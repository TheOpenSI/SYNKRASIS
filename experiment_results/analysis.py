import pandas as pd

df = pd.read_csv("experiment_results/qwen2.5-coder_mbpp_results.csv")

# Success rate
success_rate = df["status"].value_counts(normalize = True) * 100
print(success_rate)

# Attempt count
attempt_count = df["fix_mode_attempt_count"].value_counts()
print(attempt_count)

# 5 attempt count success/fail rate
attempt_5 = df[df["fix_mode_attempt_count"] == 5]["status"].value_counts()
print(attempt_5)

# Success attempt count
success_attempt_count = df[df["status"] == "pass"]["fix_mode_attempt_count"].value_counts().sort_index()
print(success_attempt_count)