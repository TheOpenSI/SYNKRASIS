import pandas as pd
import os

def calculate_debugging_influence(file_path):
    """
    Calculate the normalized influence of each self-debugging attempt.
    
    Args:
        file_path (str): Path to the CSV file containing results
        
    Returns:
        dict: Dictionary containing influence metrics for each attempt
    """
    # Read the CSV file
    df = pd.read_csv(file_path)
    
    # Get the value counts for successful attempts (status == "pass")
    pass_counts = df[df["status"] == "pass"]["fix_mode_attempt_count"].value_counts().sort_index()
    
    # Total number of problems
    N = len(df)
    
    # Initialize results dictionary
    results = {
        'total_problems': N,
        'attempts': {},
        'summary': []
    }
    
    # Calculate S_i (number of problems solved at attempt i) for each attempt
    S = {}
    for attempt in range(6):  # 0 to 5 attempts
        S[attempt] = pass_counts.get(attempt, 0)
    
    # Calculate N_i and I_i for each attempt
    cumulative_solved = 0
    
    for i in range(6):  # 0 to 5 attempts
        # N_i = N - sum of all problems solved in previous attempts
        N_i = N - cumulative_solved
        
        # S_i = number of problems solved at attempt i
        S_i = S[i]
        
        # I_i = S_i / N_i (influence of attempt i)
        if N_i > 0:
            I_i = S_i / N_i
        else:
            I_i = 0.0
        
        # Store results
        results['attempts'][i] = {
            'S_i': S_i,           # Problems solved at attempt i
            'N_i': N_i,           # Problems remaining before attempt i
            'I_i': I_i,           # Normalized influence
            'I_i_percent': I_i * 100  # Influence as percentage
        }
        
        # Update cumulative count
        cumulative_solved += S_i
        
        # Add to summary
        if N_i > 0:  # Only include attempts where there were problems to solve
            results['summary'].append(f"Attempt {i}: {S_i}/{N_i} = {I_i:.4f} ({I_i*100:.2f}%)")
    
    # Calculate overall success rate
    total_solved = sum(S.values())
    overall_success_rate = total_solved / N
    results['total_solved'] = total_solved
    results['overall_success_rate'] = overall_success_rate
    results['overall_success_percent'] = overall_success_rate * 100
    
    return results


def write_debugging_influence_log(file_path, log_file_path=None):
    """
    Write a formatted report of the debugging influence analysis to a log file.
    
    Args:
        file_path (str): Path to the CSV file containing results
        log_file_path (str): Path to the output log file. If None, creates a log file 
                           based on the input file name.
    
    Returns:
        dict: Results dictionary
    """
    results = calculate_debugging_influence(file_path)
    
    # Generate log file name if not provided
    if log_file_path is None:
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        log_file_path = f"{base_name}_influence_analysis.log"
    
    # Write to log file
    with open(log_file_path, 'w') as log_file:
        log_file.write("Self-debugging Influence Analysis\n")
        log_file.write("=" * 40 + "\n")
        log_file.write(f"File: {file_path}\n")
        log_file.write(f"Total Problems: {results['total_problems']}\n")
        log_file.write(f"Total Solved: {results['total_solved']}\n")
        log_file.write(f"Overall Success Rate: {results['overall_success_percent']:.2f}%\n")
        log_file.write("\n")
        
        log_file.write("Normalized Influence by Attempt:\n")
        log_file.write("-" * 40 + "\n")
        log_file.write(f"{'Attempt':<8} {'Solved':<8} {'Remaining':<10} {'Influence':<12} {'Percentage':<12}\n")
        log_file.write("-" * 40 + "\n")
        
        for i in range(6):
            attempt_data = results['attempts'][i]
            if attempt_data['N_i'] > 0:  # Only show attempts where problems were available
                log_file.write(f"{i:<8} {attempt_data['S_i']:<8} {attempt_data['N_i']:<10} "
                              f"{attempt_data['I_i']:.4f}{'':>6} {attempt_data['I_i_percent']:.2f}%\n")
        
        log_file.write("\n")
        log_file.write("Summary:\n")
        for summary_line in results['summary']:
            log_file.write(f"  {summary_line}\n")
    
    print(f"Analysis saved to: {log_file_path}")
    return results


def batch_analyze_files(directory_path, output_directory="analysis_logs"):
    """
    Analyze multiple CSV files in a directory and create log files for each.
    
    Args:
        directory_path (str): Directory containing CSV files
        output_directory (str): Directory to save log files
    
    Returns:
        dict: Dictionary with file names as keys and results as values
    """
    # Create output directory if it doesn't exist
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    
    all_results = {}
    csv_files = [f for f in os.listdir(directory_path) if f.endswith('.csv')]
    
    for csv_file in csv_files:
        file_path = os.path.join(directory_path, csv_file)
        base_name = os.path.splitext(csv_file)[0]
        log_file_path = os.path.join(output_directory, f"{base_name}_influence_analysis.log")
        
        try:
            results = write_debugging_influence_log(file_path, log_file_path)
            all_results[csv_file] = results
            print(f"Processed: {csv_file}")
        except Exception as e:
            print(f"Error processing {csv_file}: {str(e)}")
    
    return all_results


def consolidate_logs(log_directory, output_file="consolidated_influence_analysis.log"):
    """
    Consolidate all log files from a directory into a single file.
    
    Args:
        log_directory (str): Directory containing log files
        output_file (str): Path to the consolidated output file
    
    Returns:
        int: Number of log files consolidated
    """
    log_files = [f for f in os.listdir(log_directory) if f.endswith('.log')]
    
    if not log_files:
        print(f"No log files found in {log_directory}")
        return 0
    
    with open(output_file, 'w') as consolidated_file:
        consolidated_file.write("CONSOLIDATED SELF-DEBUGGING INFLUENCE ANALYSIS\n")
        consolidated_file.write("=" * 60 + "\n")
        consolidated_file.write(f"Generated from {len(log_files)} log files\n")
        consolidated_file.write("=" * 60 + "\n\n")
        
        for i, log_file in enumerate(sorted(log_files)):
            log_path = os.path.join(log_directory, log_file)
            
            # Add separator between files
            if i > 0:
                consolidated_file.write("\n" + "=" * 60 + "\n\n")
            
            consolidated_file.write(f"SOURCE FILE: {log_file}\n")
            consolidated_file.write("-" * 60 + "\n")
            
            # Read and write the content of each log file
            with open(log_path, 'r') as individual_log:
                content = individual_log.read()
                consolidated_file.write(content)
            
            consolidated_file.write("\n")
    
    print(f"Consolidated {len(log_files)} log files into: {output_file}")
    return len(log_files)


def analyze_and_consolidate(directory_path, log_directory="analysis_logs", 
                          consolidated_file="consolidated_influence_analysis.log"):
    """
    Complete workflow: analyze all CSV files and create a consolidated report.
    
    Args:
        directory_path (str): Directory containing CSV files
        log_directory (str): Directory to save individual log files
        consolidated_file (str): Path to the consolidated output file
    
    Returns:
        tuple: (all_results dict, number of files consolidated)
    """
    print("Step 1: Analyzing individual CSV files...")
    all_results = batch_analyze_files(directory_path, log_directory)
    
    print("\nStep 2: Consolidating log files...")
    num_consolidated = consolidate_logs(log_directory, consolidated_file)
    
    print(f"\nComplete! Analyzed {len(all_results)} files and created consolidated report.")
    return all_results, num_consolidated


if __name__ == "__main__":
    # Consolidate existing log files
    consolidate_logs("analysis_logs", "all_results.log")
    # all_results, num_files = analyze_and_consolidate("experiment_results")