import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Load the data
df = pd.read_csv("sim_experiment_results.csv")
# df = np.log(df)

plt.figure(figsize=(10, 6))
for i in range(len(df)):
    plt.plot(df.columns, df.iloc[i], marker=None, color = "blue", linewidth=0.5)
    
plt.savefig("sim_experiment_results.png", dpi=300, bbox_inches='tight')