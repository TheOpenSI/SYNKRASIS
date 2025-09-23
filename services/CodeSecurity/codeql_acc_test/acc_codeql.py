import json, os, sys, subprocess, re
from tqdm import tqdm
from pathlib import Path
from typing import Tuple, List, Union

from sariff_test import analyse_sarif

def setup_directories(base_path: str = "services/CodeSecurity/codeql_acc_test") -> Path:
    """
    Create necessary directory structure
    """
    base_path = Path(base_path)

    directories = [
        base_path / "code",
        base_path / "db", 
        base_path / "output"
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    
    return base_path


def run_codeql_analysis(sample_index: int, 
                        vul_code: str, 
                        base_path: Path, 
                        codeql_binary: Union[Path, str], 
                        bash_script_path: Path) -> Tuple[bool, str]:
    """
    Run CodeQL analysis on a single sample
    """
    code_file = base_path / "code" / "main.py"
    db_dir = base_path / "db"
    # problem_id = f"_{sample_index}_vul"
    problem_id = sample_index
    
    try:
        _create_py_file(vul_code, code_file)

        cmd = [
            bash_script_path,
            str(code_file.parent),  
            str(codeql_binary),
            str(db_dir),
            str(problem_id)
        ]
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True 
        )
        
        if result.returncode != 0:
            error_msg = f"CodeQL failed (exit code {result.returncode})"
            if result.stderr:
                error_msg += f": {result.stderr.strip()}"
            return False, error_msg
        
        return True, "Success"
        
    except Exception as e:
        return False, f"Exception during analysis: {str(e)}"
    

def _create_py_file(code: str,
                    file_path: Path) -> None:
    """
    Create a Python file with the given code.
    """
    code = _clean_python_content(code)
    with open(file_path, 'w') as f:
        f.write(code)


def _clean_python_content(code:str) -> str:
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


def main():
    df_path = "services/CodeSecurity/data/python_cyber_native.jsonl"
    codeql_binary = "/home/s448780/workspace_hcc4/codeql/codeql"
    bash_script_path = "services/CodeSecurity/codeql_acc_test/run_codeql.bash" 
    
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
    
    for i, sample in enumerate(tqdm(data, desc="Processing Code Samples")):
        try:
            vul_code = sample.get("rejected")
            
            if not vul_code:
                failed_samples.append((i, "No 'rejected' code found in sample"))
                continue
                
            if not vul_code.strip():
                failed_samples.append((i, "Empty 'rejected' code"))
                continue
            
            success, message = run_codeql_analysis(
                i, vul_code, base_path, codeql_binary, bash_script_path
            )
            
            if success:
                successful_count += 1
            else:
                failed_samples.append((i, message))
                
            vul_results = analyse_sarif(base_path / "output" / f"results{i}.sarif")
            print(f"File: results{i}.sarif, Total issues found: {len(vul_results)}")
            break
                
        except Exception as e:
            failed_samples.append((i, f"Unexpected error: {str(e)}"))
    
    print(f"\n=== Analysis Complete ===")
    print(f"Successfully processed: {successful_count}/{len(data)} samples")
    print(f"Failed samples: {len(failed_samples)}")
    
    if failed_samples:
        print(f"\nFailed Samples:")
        for sample_idx, error_msg in failed_samples:
            print(f"  Sample {sample_idx}: {error_msg}")
    
    print(f"\nResults saved in: {base_path / 'output'}")
    
    # delete the db folder at the end
    db_dir = base_path / "db"
    if db_dir.exists() and db_dir.is_dir():
        for item in db_dir.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                import shutil
                shutil.rmtree(item)
        db_dir.rmdir()


if __name__ == "__main__":
    main()