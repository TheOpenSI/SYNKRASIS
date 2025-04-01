import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import csv
import io

def log_function(x, a, b):
    return a + b * np.log(x)

df = pd.read_csv("sim_experiment_results.csv")

# Calculate the mean value for each attempt column
mean_values = df.mean()

# Create x-values (attempt numbers 1 through 10)
x_data = np.array(range(1, len(mean_values) + 1))
y_data = mean_values.values

try:
    # Initial parameter guesses
    initial_guess = [max(y_data), -5]
    
    # Perform the curve fitting
    params, covariance = curve_fit(log_function, x_data, y_data, p0=initial_guess)
    
    # Extract the optimized parameters
    a_opt, b_opt = params
    
    # Calculate R-squared value to assess goodness of fit
    y_fit = log_function(x_data, a_opt, b_opt)
    residuals = y_data - y_fit
    ss_res = np.sum(residuals**2)
    ss_tot = np.sum((y_data - np.mean(y_data))**2)
    r_squared = 1 - (ss_res / ss_tot)
    
    # Print the results
    print(f"Fitted logarithmic function: y = {a_opt:.4f} + {b_opt:.4f} * ln(x)")
    print(f"R-squared: {r_squared:.4f}")
    
    # Calculate the initial value (at x=1)
    initial_value = log_function(1, a_opt, b_opt)
    
    # Calculate various threshold points
    thresholds = [0.5, 0.2, 0.1, 0.05]  # 50%, 20%, 10%, 5% of initial value
    threshold_points = {}
    
    for threshold in thresholds:
        target_value = initial_value * threshold
        threshold_x = np.exp((target_value - a_opt) / b_opt)
        threshold_points[threshold] = threshold_x
        
        print(f"\nValue reduces to {threshold*100:.0f}% of initial after {threshold_x:.2f} attempts")
        print(f"This represents a {(1-threshold)*100:.0f}% reduction from the initial value")
    
    # Plot the original data points and the fitted curve
    plt.figure(figsize=(12, 7))
    plt.scatter(x_data, y_data, label='Data Points (Mean Values)', s=60)
    
    # Generate a smoother curve for plotting
    x_smooth = np.linspace(min(x_data), max(x_data) + 5, 100)
    y_smooth = log_function(x_smooth, a_opt, b_opt)
    plt.plot(x_smooth, y_smooth, 'r-', linewidth=2, label=f'Fitted: {a_opt:.2f} + {b_opt:.2f} * ln(x)')
    
    # Mark the threshold points
    colors = ['g', 'b', 'orange', 'purple']
    for i, (threshold, x_val) in enumerate(threshold_points.items()):
        y_val = initial_value * threshold
        color = colors[i]
        
        # plt.axvline(x=x_val, color=color, linestyle='--', alpha=0.7)
        # plt.axhline(y=y_val, color=color, linestyle='--', alpha=0.7)
        plt.scatter([x_val], [y_val], color=color, s=100, zorder=5)
        # plt.text(x_val + 0.2, y_val, f'{threshold*100:.0f}% of initial ({(1-threshold)*100:.0f}% reduction)\nat attempt {x_val:.2f}', 
        #          color=color, fontweight='bold')
        plt.text(x_val + 0.2, y_val, f'{(1-threshold)*100:.0f}% loss\nat {x_val:.2f}', color = color)
    
    plt.xlabel('Attempt Number')
    plt.ylabel('Value')
    plt.title('Logarithmic Function with Various Reduction Thresholds')
    plt.legend()
    plt.grid(True)
    plt.xlim(0, max(15, max(threshold_points.values()) + 1))
    plt.savefig('logarithmic_fit.png')
    
except Exception as e:
    print(f"Error during curve fitting: {e}")

# To use this with an actual CSV file, replace the io.StringIO part with:
# df = pd.read_csv('your_data.csv')=1, ln(1)=