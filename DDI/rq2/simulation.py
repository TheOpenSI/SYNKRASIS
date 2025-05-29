import numpy as np
import matplotlib.pyplot as plt
from typing import List, Tuple, Optional

class DDI:
    def __init__(self, 
                 theta: float = 80, 
                 min_attempts: int = 2, 
                 max_attempts: int = 10):
        """
        DDI implementation
        
        Args:
            theta: Decay threshold percentage (0-100)
            min_attempts: Minimum debugging attempts before stopping
            max_attempts: Maximum debugging attempts (safety cap)
        """
        self.theta = theta
        self.min_attempts = min_attempts
        self.max_attempts = max_attempts
        self.reset()
        
    def calculate_independent_influence(data):
        """
        Calculate I_i = S_i / N_i for each debugging attempt
        """
        total_problems = len(data)
        successes_at_attempt = {}
        
        # Count successes at each attempt
        for attempt, success in data:
            if attempt not in successes_at_attempt:
                successes_at_attempt[attempt] = 0
            if success:
                successes_at_attempt[attempt] += 1
        
        # Calculate independent influence
        cumulative_successes = 0
        influence_values = {}
        
        max_attempt = max(attempt for attempt, _ in data)
        for i in range(max_attempt + 1):
            problems_remaining = total_problems - cumulative_successes
            successes_at_i = successes_at_attempt.get(i, 0)
            
            influence_values[i] = successes_at_i / problems_remaining if problems_remaining > 0 else 0
            cumulative_successes += successes_at_i
        
        return influence_values
    
    
    def reset(self):
        """Reset for new problem"""
        self.effectiveness_history = []
        self.lambda_estimates = []
    
    
    def estimate_lambda(self) -> Optional[float]:
        """Estimate decay constant from current effectiveness history"""
        if len(self.effectiveness_history) < 2:
            return None
        
        # Convert to numpy arrays
        attempts = np.array(range(len(self.effectiveness_history)))
        effectiveness = np.array(self.effectiveness_history)
        
        # Avoid log(0) by adding small epsilon
        effectiveness = np.maximum(effectiveness, 1e-6)
        log_effectiveness = np.log(effectiveness)
        
        try:
            # Linear regression: log(E) = log(E0) - λt
            slope, _ = np.polyfit(attempts, log_effectiveness, 1)
            lambda_est = -slope
            return max(0, lambda_est)  # Ensure non-negative
        except:
            return None
    
    
    def calculate_optimal_attempts(self, lambda_val: float) -> int:
        """Calculate optimal attempts using your Equation 3"""
        if lambda_val <= 0:
            return self.max_attempts
        
        # t_θ = ln(100/(100-θ)) / λ
        optimal = np.log(100 / (100 - self.theta)) / lambda_val
        return int(np.ceil(optimal))
    
    
    def should_continue(self, current_effectiveness: float, attempt_num: int) -> bool:
        """Decide whether to continue debugging"""
        self.effectiveness_history.append(current_effectiveness)
        
        # Always do minimum attempts
        if attempt_num < self.min_attempts:
            return True
        
        # Never exceed maximum
        if attempt_num >= self.max_attempts:
            return False
        
        # Estimate lambda and make decision
        lambda_est = self.estimate_lambda()
        if lambda_est is None or lambda_est <= 0.01:  # Very slow decay
            return attempt_num < self.max_attempts
        
        self.lambda_estimates.append(lambda_est)
        optimal_attempts = self.calculate_optimal_attempts(lambda_est)
        
        return attempt_num < optimal_attempts


def simulate_problem(initial_effectiveness: float, decay_rate: float, noise: float = 0.1) -> List[float]:
    """
    Simulate debugging effectiveness for a single problem
    
    Args:
        initial_effectiveness: E0 value (0-1)
        decay_rate: True lambda value for this problem
        noise: Random noise level
    
    Returns:
        List of effectiveness values over attempts
    """
    max_sim_attempts = 15
    effectiveness_curve = []
    
    for t in range(max_sim_attempts):
        # True exponential decay with noise
        true_eff = initial_effectiveness * np.exp(-decay_rate * t)
        noisy_eff = true_eff * (1 + np.random.normal(0, noise))
        noisy_eff = max(0, min(1, noisy_eff))  # Clamp to [0,1]
        effectiveness_curve.append(noisy_eff)
    
    return effectiveness_curve


def run_simulation(num_problems: int = 100, theta: float = 80):
    """Run complete simulation"""
    
    # Initialize DDI
    ddi = DDI(theta=theta)
    
    # Track results
    results = {
        'problem_id': [],
        'true_lambda': [],
        'estimated_lambda': [],
        'attempts_used': [],
        'optimal_attempts': [],
        'final_effectiveness': [],
        'initial_effectiveness': []
    }
    
    print(f"Running simulation with {num_problems} problems (theta={theta}%)")
    print("-" * 60)
    
    for problem_id in range(num_problems):
        # Generate random problem characteristics
        initial_eff = np.random.uniform(0.1, 0.8)  # E0
        true_lambda = np.random.uniform(0.1, 1.5)  # Decay rate
        
        # Generate effectiveness curve for this problem
        effectiveness_curve = simulate_problem(initial_eff, true_lambda)
        
        # Reset DDI for new problem
        ddi.reset()
        
        # Simulate debugging process
        attempts_used = 0
        for attempt in range(len(effectiveness_curve)):
            current_eff = effectiveness_curve[attempt]
            
            if not ddi.should_continue(current_eff, attempt):
                break
            attempts_used = attempt + 1
        
        # Calculate what optimal would have been
        optimal_attempts_true = int(np.ceil(np.log(100 / (100 - theta)) / true_lambda))
        
        # Get final estimated lambda
        final_lambda_est = ddi.estimate_lambda() if len(ddi.lambda_estimates) > 0 else None
        
        # Store results
        results['problem_id'].append(problem_id)
        results['true_lambda'].append(true_lambda)
        results['estimated_lambda'].append(final_lambda_est)
        results['attempts_used'].append(attempts_used)
        results['optimal_attempts'].append(optimal_attempts_true)
        results['final_effectiveness'].append(effectiveness_curve[attempts_used-1] if attempts_used > 0 else initial_eff)
        results['initial_effectiveness'].append(initial_eff)
        
        # Print progress for first few problems
        if problem_id < 5:
            lambda_est_str = f"{final_lambda_est:.3f}" if final_lambda_est is not None else "  None"
            print(f"Problem {problem_id}: E0={initial_eff:.3f}, λ_true={true_lambda:.3f}, "
                f"λ_est={lambda_est_str:>6}, attempts={attempts_used}, optimal={optimal_attempts_true}")

    
    return results


def analyze_results(results: dict):
    """Analyze simulation results"""
    print("\n" + "="*60)
    print("SIMULATION RESULTS ANALYSIS")
    print("="*60)
    
    # Convert to numpy arrays for analysis
    true_lambdas = np.array(results['true_lambda'])
    est_lambdas = np.array([x for x in results['estimated_lambda'] if x is not None])
    attempts_used = np.array(results['attempts_used'])
    optimal_attempts = np.array(results['optimal_attempts'])
    
    # Lambda estimation accuracy
    valid_estimates = [(t, e) for t, e in zip(results['true_lambda'], results['estimated_lambda']) if e is not None]
    if valid_estimates:
        true_vals, est_vals = zip(*valid_estimates)
        mae_lambda = np.mean(np.abs(np.array(true_vals) - np.array(est_vals)))
        print(f"Lambda Estimation MAE: {mae_lambda:.3f}")
    
    # Attempt efficiency
    mae_attempts = np.mean(np.abs(attempts_used - optimal_attempts))
    print(f"Attempts vs Optimal MAE: {mae_attempts:.3f}")
    print(f"Average attempts used: {np.mean(attempts_used):.1f}")
    print(f"Average optimal attempts: {np.mean(optimal_attempts):.1f}")
    
    # Efficiency ratio
    efficiency = attempts_used / np.maximum(optimal_attempts, 1)
    print(f"Efficiency ratio (used/optimal): {np.mean(efficiency):.3f} ± {np.std(efficiency):.3f}")
    
    return results


def plot_results(results: dict):
    """Plot simulation results"""
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # Lambda estimation accuracy
    valid_pairs = [(t, e) for t, e in zip(results['true_lambda'], results['estimated_lambda']) if e is not None]
    if valid_pairs:
        true_vals, est_vals = zip(*valid_pairs)
        axes[0,0].scatter(true_vals, est_vals, alpha=0.6)
        axes[0,0].plot([0, max(true_vals)], [0, max(true_vals)], 'r--', alpha=0.8)
        axes[0,0].set_xlabel('True Lambda')
        axes[0,0].set_ylabel('Estimated Lambda')
        axes[0,0].set_title('Lambda Estimation Accuracy')
    
    # Attempts comparison
    axes[0,1].scatter(results['optimal_attempts'], results['attempts_used'], alpha=0.6)
    max_attempts = max(max(results['optimal_attempts']), max(results['attempts_used']))
    axes[0,1].plot([0, max_attempts], [0, max_attempts], 'r--', alpha=0.8)
    axes[0,1].set_xlabel('Optimal Attempts')
    axes[0,1].set_ylabel('Used Attempts')
    axes[0,1].set_title('Attempts: Used vs Optimal')
    
    # Efficiency distribution
    efficiency = np.array(results['attempts_used']) / np.maximum(results['optimal_attempts'], 1)
    axes[1,0].hist(efficiency, bins=20, alpha=0.7)
    axes[1,0].axvline(1.0, color='red', linestyle='--', label='Perfect Efficiency')
    axes[1,0].set_xlabel('Efficiency Ratio (Used/Optimal)')
    axes[1,0].set_ylabel('Frequency')
    axes[1,0].set_title('Efficiency Distribution')
    axes[1,0].legend()
    
    # Lambda vs Attempts
    axes[1,1].scatter(results['true_lambda'], results['attempts_used'], alpha=0.6)
    axes[1,1].set_xlabel('True Lambda (Decay Rate)')
    axes[1,1].set_ylabel('Attempts Used')
    axes[1,1].set_title('Decay Rate vs Attempts Used')
    
    plt.tight_layout()
    plt.savefig("DDI/rq2/simulation_results.png")

if __name__ == "__main__":
    # Run simulation
    results = run_simulation(num_problems=50, theta=80)
    
    # Analyze results
    analyze_results(results)
    
    # Plot results
    plot_results(results)
    
    # Test different theta values
    print("\n" + "="*60)
    print("TESTING DIFFERENT THETA VALUES")
    print("="*60)
    
    for theta in [50, 70, 80, 90, 95]:
        results_theta = run_simulation(num_problems=20, theta=theta)
        avg_attempts = np.mean(results_theta['attempts_used'])
        print(f"Theta {theta:2d}%: Average attempts = {avg_attempts:.1f}")