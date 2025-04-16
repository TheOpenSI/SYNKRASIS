import pandas as pd
pd.set_option('display.float_format', '{:.4f}'.format)

df = pd.read_csv("token_usage/token_usage.csv")

df["dataset_len"] = df["Dataset"].apply(lambda x: 164 if "human" in x else (974 if "mbpp" in x else 1140))
df["Average_tokens_per_problem"] = df["Tokens"] / df["dataset_len"]
# Average
grouped = df.groupby(["Model", "Dataset"])[["Tokens", 
                                            "Average_tokens_per_problem", 
                                            "Average_attempts_per_problem"]].mean().reset_index()
print(grouped)
# Save the grouped DataFrame to a CSV file
grouped.to_csv("token_usage/grouped_usage.csv", index=False)
# df.to_csv("token_usage/token_usage_test.csv", index=False)