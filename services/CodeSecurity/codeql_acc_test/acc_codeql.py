import json, os, sys, subprocess
from tqdm import tqdm
from pathlib import Path
from typing import Tuple, List, Union

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
    code_file = base_path / "code" / f"sample_{sample_index}_vul.py"
    db_dir = base_path / "db"
    # problem_id = f"_{sample_index}_vul"
    problem_id = sample_index
    
    try:
        with open(code_file, 'w') as f:
            f.write(vul_code)
        
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
                
            # break
                
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