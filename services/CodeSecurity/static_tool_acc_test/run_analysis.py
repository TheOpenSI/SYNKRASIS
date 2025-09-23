import json, os, sys, subprocess, re
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from tqdm import tqdm
from pathlib import Path
from typing import Tuple, List, Union

from services.CodeSecurity.static_tool_acc_test.analysis.ql import analyse_sarif
from services.CodeSecurity.static_tool_acc_test.analysis.sg import analyse_sg_json

def setup_directories(base_path: str = "services/CodeSecurity/static_tool_acc_test") -> Path:
    """
    Create necessary directory structure
    
    Args:
        base_path (str): The base directory where subdirectories will be created.
    """
    base_path = Path(base_path)

    directories = [
        base_path / "vul_code",
        base_path / "db", 
        base_path / "output_ql",
        base_path / "output_sem",
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    
    return base_path


def create_py_file(code: str,
                    file_path: Path) -> None:
    """
    Create a Python file with the given code.
    """
    code = clean_python_content(code)
    with open(file_path, 'w') as f:
        f.write(code)


def clean_python_content(code:str) -> str:
    """
    Remove unwanted characters from the Python code.

    Args:
        code (str): The original Python code.

    Returns:
        str: The cleaned Python code.
    """
    # Remove ```python and ``` markers
    pattern = r"```(python)?\s*|```"
    code = re.sub(pattern, "", code)
    return code.strip()


def ql_analysis_cmd(bash_script_path: Path, 
                    code_file: Path, 
                    codeql_binary: Union[Path, str], 
                    db_dir: Path, 
                    problem_id: int) -> list:
    """
    Construct the CodeQL analysis command.
    """
    cmd = [
            "bash",
            bash_script_path,
            str(code_file.parent),  
            str(codeql_binary),
            str(db_dir),
            str(problem_id)
        ]
    return cmd


def semgrep_analysis_cmd(bash_script_path: Path,
                         code_file: Path,
                         problem_id: int) -> list:
    """
    Construct the Semgrep analysis command.
    """
    cmd = [
            "bash",
            bash_script_path,
            str(code_file.parent),  
            str(problem_id)
        ]
    return cmd


def run_analysis(sample_index: int, 
                 vul_code: str, 
                 base_path: Path, 
                 codeql_binary: Union[Path, str], 
                 ql_bash_script_path: Path,
                 sg_bash_script_path: Path) -> List[Tuple[bool, str]]:
    """
    Run CodeQL and Semgrep analysis on the provided code snippet.

    Args:
        sample_index (int): Problem/sample index.
        vul_code (str): Vulnerability code snippet.
        base_path (Path): Base directory path.
        codeql_binary (Union[Path, str]): Path to CodeQL binary.
        ql_bash_script_path (Path): Path to CodeQL bash script.
        sg_bash_script_path (Path): Path to Semgrep bash script.

    Returns:
        List[Tuple[bool, str]]: List of tuples indicating success status and messages for each tool.
    """
    code_file = base_path / "vul_code" / "main.py"
    db_dir = base_path / "db"
    # problem_id = f"_{sample_index}_vul"
    problem_id = sample_index

    # creates main.py file in vul_code directory
    create_py_file(vul_code, code_file)

    # codeql command
    ql_command = ql_analysis_cmd(ql_bash_script_path,code_file,codeql_binary,db_dir,problem_id)
    
    # semgrep command
    sg_command = semgrep_analysis_cmd(sg_bash_script_path,code_file,problem_id)
    
    results = [(False, "Not executed"), (False, "Not executed")]
    
    for i, cmd in enumerate([ql_command, sg_command]):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
                
            if result.returncode != 0:
                static_tool = "Semgrep" if i == 1 else "CodeQL"
                error_msg = f"{static_tool} failed (exit code {result.returncode})"
                if result.stderr:
                    error_msg += f": {result.stderr.strip()}"
                results[i] = (False, error_msg)  # Use index assignment
            else:
                static_tool = "Semgrep" if i == 1 else "CodeQL"
                results[i] = (True, f"{static_tool} completed")
            
        except Exception as e:
            static_tool = "Semgrep" if i == 1 else "CodeQL"
            results[i] = (False, f"{static_tool} exception: {str(e)}")
        
    return results
         
         
def handle_missing_vul_code(i:int,
                            vul_code:str,
                            failed_samples: list) -> bool:
    """
    Check if the vulnerability code is missing or empty.
    
    Args:
        vul_code (str): The vulnerability code snippet.
    
    Returns:
        bool: True if the code is missing or empty, False otherwise.
    """
    if not vul_code:
        failed_samples.append((i, "No 'rejected' code found in sample"))
        return True
        
    if not vul_code.strip():
        failed_samples.append((i, "Empty 'rejected' code"))
        return True

    return False


def handle_run_results(results: List[Tuple[bool, str]]) -> Tuple[bool, bool, bool]:
    """
    Analyze the results of the static analysis runs.

    Args:
        results (List[Tuple[bool, str]]): List of tuples indicating success status and messages for each tool.

    Returns:
        Tuple[bool, bool, bool]: A tuple indicating (both_run_success, codeql_success, semgrep_success).
    """
    both_run_success = all([success for success, _ in results])
    codeql_success = results[0][0]
    semgrep_success = results[1][0]
    return both_run_success, codeql_success, semgrep_success
    
    
    
def main():
    df_path = "services/CodeSecurity/data/python_cyber_native.jsonl"
    codeql_binary = "/home/s448780/workspace_hcc4/codeql/codeql"
    ql_bash_script_path = "services/CodeSecurity/static_tool_acc_test/run_codeql.bash"
    sg_bash_script_path = "services/CodeSecurity/static_tool_acc_test/run_semgrep.bash"
    
    print("Setting up directory structure...")
    base_path = setup_directories()
    
    print("Loading dataset...")
    try:
        with open(df_path, 'r') as f:
            data = [json.loads(line) for line in f]
    
    except Exception as e:
        print(f"Error loading data: {e}")
        sys.exit(1)
    
    failed_samples = []
    successful_count = 0
    
    print("Starting analysis...")
    for i, sample in enumerate(tqdm(data, desc="Processing Code Samples")):
        try:
            vul_code = sample.get("rejected")
            
            if handle_missing_vul_code(i, vul_code, failed_samples):
                continue
            
            run_results = run_analysis(
                i, vul_code, base_path, codeql_binary, ql_bash_script_path, sg_bash_script_path
            )
            both_run_success, codeql_success, semgrep_success = handle_run_results(run_results)
            ql_results = sg_results = []
            if both_run_success:
                successful_count += 1
                ql_results = analyse_sarif(base_path / "output" / f"results{i}.sarif")
                sg_results = analyse_sg_json(base_path / "output_sem" / f"results{i}.json")
            
            else:
                if not codeql_success:
                    failed_samples.append((i, "CodeQL analysis failed", vul_code))
                    sg_results = analyse_sg_json(base_path / "output_sem" / f"results{i}.json")
                if not semgrep_success:
                    failed_samples.append((i, "Semgrep analysis failed", vul_code))
                    ql_results = analyse_sarif(base_path / "output" / f"results{i}.sarif")
            
            print(f"Sample {i} | CodeQl: {len(ql_results)} results | Semgrep: {len(sg_results)} results")
            
            break
                
        except Exception as e:
            failed_samples.append((i, f"Unexpected error: {str(e)}", vul_code))



if __name__ == "__main__":
    main()