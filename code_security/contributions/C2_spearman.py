from scipy import stats
import numpy as np

# Perfect Agreement data from tables
sven = [81.87, 63.74, 71.64, 50.88, 66.96, 23.98, 73.39]
seceval = [61.98, 20.66, 21.49, 16.53, 34.71, 8.26, 52.07]

# Correlation
spearman, p = stats.spearmanr(sven, seceval)
print(f"Spearman correlation: rho = {spearman:.2f}, p = {p:.4f}")

# Gap between Perfect and Majority
sven_majority = [92.98, 86.84, 89.77, 75.73, 91.23, 72.51, 91.81]
seceval_majority = [86.78, 56.20, 62.81, 55.37, 71.90, 49.59, 85.95]

sven_gap = np.mean([m - p for m, p in zip(sven_majority, sven)])
seceval_gap = np.mean([m - p for m, p in zip(seceval_majority, seceval)])

print(f"\nAverage gap (Majority - Perfect):")
print(f"  SVEN: {sven_gap:.1f} percentage points")
print(f"  SecurityEval: {seceval_gap:.1f} percentage points")