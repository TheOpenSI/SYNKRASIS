import random
import numpy as np
import pandas as pd

# Simulate the data for the experiment
attempt_1 = list(range(20, 30))
attempt_2 = list(range(5, 11))
attempt_3 = list(range(3, 6))
attempt_4 = list(range(1, 4))
attempt_5 = list(range(1, 3))
attempt_6 = np.linspace(0.0, 0.9, 10).tolist()
attempt_7 = np.linspace(0.0, 0.9, 10).tolist()
attempt_8 = np.linspace(0.0, 0.9, 10).tolist()
attempt_9 = np.linspace(0.0, 0.9, 10).tolist()
attempt_10 = np.linspace(0.0, 0.9, 10).tolist()

attempt_ranges = [attempt_1, attempt_2, attempt_3, 
                  attempt_4, attempt_5, attempt_6, 
                  attempt_7, attempt_8, attempt_9, 
                  attempt_10]


data = []
for row_num in range(100):
    temp_row = {}
    for i, attempt in enumerate(attempt_ranges):
        temp_row[f"attempt_{i+1}"] = round(float(random.choice(attempt)), 2)
    data.append(temp_row)

# DataFrame
df = pd.DataFrame(data)
df.to_csv("sim_experiment_results.csv", index=False)
