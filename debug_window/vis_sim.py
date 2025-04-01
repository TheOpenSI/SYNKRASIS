import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

# # Load the data
# df = pd.read_csv("sim_experiment_results.csv")
# # df = np.log(df)

# plt.figure(figsize=(10, 6))
# for i in range(len(df)):
#     plt.plot(df.columns, df.iloc[i], marker=None, color = "blue", linewidth=0.5)
    
# plt.savefig("sim_experiment_results.png", dpi=300, bbox_inches='tight')
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import csv
import io

# Define the logarithmic function y = a + b * ln(x)
def log_function(x, a, b):
    return a + b * np.log(x)

# Define an exponential decay function (for comparison)
def exp_decay(x, A, lambda_val):
    return A * np.exp(-lambda_val * x)

df = pd.read_csv("sim_experiment_results.csv")

# Calculate the mean value for each attempt column
mean_values = df.mean()

# Create x-values (attempt numbers 1 through 10)
x_data = np.array(range(1, len(mean_values) + 1))
y_data = mean_values.values

# Display the raw data
print("Mean values for each attempt:")
for i, val in enumerate(y_data):
    print(f"Attempt {i+1}: {val:.4f}")

# Calculate the improvement rate (change between consecutive attempts)
improvements = [y_data[i] - y_data[i+1] for i in range(len(y_data)-1)]
improvement_rates = [improvements[i]/y_data[i] * 100 for i in range(len(improvements))]

print("\nImprovement rates between consecutive attempts:")
for i, rate in enumerate(improvement_rates):
    print(f"From attempt {i+1} to {i+2}: {rate:.2f}%")

# Fit the logarithmic function to the data
try:
    # Initial parameter guesses
    initial_guess = [max(y_data), -5]
    
    # Perform the curve fitting
    params_log, covariance_log = curve_fit(log_function, x_data, y_data, p0=initial_guess)
    
    # Extract the optimized parameters
    a_opt, b_opt = params_log
    
    # Calculate R-squared value to assess goodness of fit
    y_fit_log = log_function(x_data, a_opt, b_opt)
    residuals_log = y_data - y_fit_log
    ss_res_log = np.sum(residuals_log**2)
    ss_tot = np.sum((y_data - np.mean(y_data))**2)
    r_squared_log = 1 - (ss_res_log / ss_tot)
    
    # Also fit exponential decay for comparison
    initial_guess_exp = [y_data[0], 0.5]
    params_exp, covariance_exp = curve_fit(exp_decay, x_data, y_data, p0=initial_guess_exp)
    A_opt, lambda_opt = params_exp
    half_life = np.log(2) / lambda_opt
    
    # Calculate R-squared for exponential model
    y_fit_exp = exp_decay(x_data, A_opt, lambda_opt)
    residuals_exp = y_data - y_fit_exp
    ss_res_exp = np.sum(residuals_exp**2)
    r_squared_exp = 1 - (ss_res_exp / ss_tot)
    
    # Find the "point of diminishing returns" using second derivative of logarithmic function
    # The second derivative of a*ln(x)+b is -a/x^2, which is always negative for positive a
    # We'll use a threshold approach to determine where improvement significantly slows
    # Calculating predicted improvements between consecutive attempts
    x_pred = np.arange(1, 15)  # Extend beyond current data to see trend
    y_pred = log_function(x_pred, a_opt, b_opt)
    pred_improvements = [y_pred[i] - y_pred[i+1] for i in range(len(y_pred)-1)]
    
    # Find where improvement drops below 5% of the maximum improvement
    threshold = 0.05 * max(abs(b_opt / x) for x in x_data[1:])
    optimal_attempts = next((i for i, imp in enumerate(pred_improvements) 
                            if abs(imp) < threshold), len(x_data))
    
    # Print the results
    print("\nFitted logarithmic function: y = {:.4f} + {:.4f} * ln(x)".format(a_opt, b_opt))
    print(f"R-squared (logarithmic): {r_squared_log:.4f}")
    print(f"\nFitted exponential decay: y = {A_opt:.4f} * exp(-{lambda_opt:.4f} * x)")
    print(f"R-squared (exponential): {r_squared_exp:.4f}")
    print(f"Half-life from exponential model: {half_life:.4f} attempts")
    print(f"\nEstimated optimal number of attempts: {optimal_attempts}")
    
    # Plot the original data points and both fitted curves
    plt.figure(figsize=(12, 8))
    
    # Plot data points
    plt.scatter(x_data, y_data, label='Data Points (Mean Values)', s=50)
    
    # Generate smoother curves for plotting
    x_smooth = np.linspace(min(x_data), max(x_data)+5, 100)
    y_smooth_log = log_function(x_smooth, a_opt, b_opt)
    y_smooth_exp = exp_decay(x_smooth, A_opt, lambda_opt)
    
    plt.plot(x_smooth, y_smooth_log, 'r-', linewidth=2, 
             label=f'Logarithmic: {a_opt:.2f} + {b_opt:.2f} * ln(x)')
    plt.plot(x_smooth, y_smooth_exp, 'g--', linewidth=2,
             label=f'Exponential: {A_opt:.2f} * exp(-{lambda_opt:.2f} * x)')
    
    # Mark the optimal number of attempts
    plt.axvline(x=optimal_attempts, color='blue', linestyle='--')
    plt.text(optimal_attempts+0.1, max(y_data)/2, 
             f'Optimal attempts ≈ {optimal_attempts}', rotation=0)
    
    # Mark the half-life
    plt.axvline(x=half_life, color='green', linestyle=':')
    plt.text(half_life+0.1, max(y_data)/3, 
             f'Half-life = {half_life:.2f}', rotation=0)
    
    # Add a second y-axis for the improvement rate
    ax2 = plt.gca().twinx()
    ax2.plot(x_data[:-1], improvement_rates, 'm-', marker='o', label='Improvement Rate (%)')
    ax2.set_ylabel('Improvement Rate (%)', color='m')
    ax2.tick_params(axis='y', labelcolor='m')
    
    # Formatting
    plt.xlabel('Attempt Number')
    plt.ylabel('Value')
    plt.title('Logarithmic and Exponential Fits with Optimization Analysis')
    plt.legend(loc='upper right')
    plt.grid(True)
    plt.show()
    
    # Create a cost-benefit analysis
    # Assuming each attempt has an increasing cost (simplistic model)
    base_cost = 1.0  # Base cost of each attempt
    cost_factor = 1.2  # Cost increases by this factor with each attempt
    
    costs = [base_cost * (cost_factor ** i) for i in range(len(x_data))]
    cumulative_costs = np.cumsum(costs)
    
    # Calculate the benefit (improvement) for each attempt
    benefits = [y_data[0] - y_data[i] for i in range(len(y_data))]
    
    # Calculate benefit-to-cost ratio
    benefit_cost_ratio = [benefits[i]/cumulative_costs[i] for i in range(len(benefits))]
    
    # Plot cost-benefit analysis
    plt.figure(figsize=(12, 8))
    
    ax1 = plt.subplot(2, 1, 1)
    ax1.plot(x_data, benefits, 'b-', marker='o', label='Cumulative Improvement')
    ax1.plot(x_data, cumulative_costs, 'r-', marker='s', label='Cumulative Cost')
    ax1.set_xlabel('Attempt Number')
    ax1.set_ylabel('Value')
    ax1.legend()
    ax1.grid(True)
    ax1.set_title('Cost vs. Benefit Analysis')
    
    ax2 = plt.subplot(2, 1, 2)
    ax2.plot(x_data, benefit_cost_ratio, 'g-', marker='d')
    ax2.set_xlabel('Attempt Number')
    ax2.set_ylabel('Benefit-to-Cost Ratio')
    ax2.grid(True)
    ax2.set_title('Benefit-to-Cost Ratio by Attempt')
    
    # Find the optimal attempt number based on benefit-to-cost ratio
    optimal_cost_benefit = np.argmax(benefit_cost_ratio) + 1
    ax2.axvline(x=optimal_cost_benefit, color='red', linestyle='--')
    ax2.text(optimal_cost_benefit+0.1, max(benefit_cost_ratio)/2, 
             f'Optimal: {optimal_cost_benefit}', color='red')
    
    plt.tight_layout()
    plt.savefig("cost_benefit_analysis.png", dpi=300, bbox_inches='tight')
    
except Exception as e:
    print(f"Error during curve fitting: {e}")

# To use this with an actual CSV file, replace the io.StringIO part with:
# df = pd.read_csv('your_data.csv')