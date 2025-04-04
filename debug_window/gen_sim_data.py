import random
import numpy as np
import pandas as pd

# Simulate the data for the experiment
attempt_1 = np.linspace(15.0, 25.0, 100).tolist()
attempt_2 = np.linspace(5.0, 10.0, 100).tolist()
attempt_3 = np.linspace(2.6, 5.0, 100).tolist()
attempt_4 = np.linspace(1.3, 3.0, 100).tolist()
attempt_5 = np.linspace(1.2, 2.0, 100).tolist()
attempt_6 = np.linspace(0.0, 1.0, 10).tolist()
attempt_7 = np.linspace(0.0, 1.0, 10).tolist()
attempt_8 = np.linspace(0.0, 1.0, 10).tolist()
attempt_9 = np.linspace(0.0, 1.0, 10).tolist()
attempt_10 = np.linspace(0.0, 1.0, 10).tolist()

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
