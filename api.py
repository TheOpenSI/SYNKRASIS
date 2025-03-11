# ===============================================================================
# Description: API for PyCapsule
# Port: 8780
# For Ollama container usage, hard coded port no to 11374
# List of Endpoints:
#   - /config
#   - /query
#   - /setenv
# /config: model_medium = ollama (ollama/openai), 
#          model_name = qwen2.5-coder, 
#          maximum_attempts = 5, 
#          conversation_history = 1, 
#          image_name = synkrasis, 
#          container_name = synkrasis_alpha, 
#          mount_dir_name = synk_mount, 
#          shell_script_name = start.sh
# 
# /query:  query
# 
# /setenv: OPENAI_API_KEY
#          HUGGING_FACE_TOKEN
# ===============================================================================
import yaml
import uvicorn
import subprocess
import os
from dotenv import load_dotenv
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, RootModel

from utils.output_message_format.output_colour import print_info

ascii_art = """
 __       __        __   __             ___ 
|__) \ / /  `  /\  |__) /__` |  | |    |__  
|     |  \__, /--\ |    .__/ \__/ |___ |___ 
                                                               
"""
print()
print(ascii_art)
print("="*40)
print("Started PyCapsule Service at port 8780")
print("="*40)

app = FastAPI()

# ===============================================================================
# Pydantic Models
class ConfigUpdate(BaseModel):
    model_medium: str = None
    model_name: str = None
    maximum_attempts: int = None
    conversation_history: int = None
    ollama_container_name: str = None

# User Query
class Query(BaseModel):
    query: str
    

# Environment Variables
class Environment(RootModel):
    root: Dict[str, Optional[str]]

    def items(self):
        return self.root.items()
    
    def keys(self):
        return self.root.keys()
# ===============================================================================

def update_yaml_config(updates: Dict[str, Any]) -> None:
    """
    Update the PyCapsule configuration in the yaml file.

    Args:
        updates (Dict[str, Any]): Updates to the configuration.
    """
    config_path = "config_files/pycapsule.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    for key, value in updates.items():
        if value is not None:
            config[key] = value
                
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)
    f.close()
    
    with open(config_path, "r") as f:
        print_info(f"Updated configuration: {yaml.safe_load(f)}")
    f.close()


def start_pycapsule(query: str) -> None:
    """
    Start the PyCapsule service.
    """
    return subprocess.Popen(["python", "main.py", "--query", query],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True)


def get_py_content(file_path: str) -> str:
    """
    Get the content of the Python file.

    Args:
        file_path (str): Path to the Python file.

    Returns:
        str: Content of the Python file.
    """
    with open(file_path, "r") as f:
        return f.read()
    

@app.post("/config")
async def update_config(config_update: ConfigUpdate):
    """
    Update the PyCapsule configuration.
    """
    try:
        updates = config_update.model_dump(exclude_unset=True)
        print_info(f"Received configuration updates: {updates}")
        
        if not updates:
            raise HTTPException(status_code=400, detail="No valid updates provided")
        
        update_yaml_config(updates)
        
        return {
            "message": f"Configuration updated for {list(updates.keys())}",
            "status": "success"
        }, 200
    
    except Exception as e:
        raise HTTPException(status_code=500, 
                            detail=f"Failed to update configuration: {str(e)}")


@app.post("/query")
async def handle_query(query: Query):
    """
    Handle the user query.
    """
    try:
        print_info(f"Received query: {query.query}")
        process = start_pycapsule(query.query)
        stdout, stderr = process.communicate()
        print(stdout)
        code = get_py_content("services/Container/mount_dir/synk_mount/main.py")
        if stderr == "":
            return {
                "response": stdout,
                "code": code,
                "status": "success"
            }, 200
        else:
            return {
                "response": f"Full Response: {stdout}",
                "error": stderr,
                "code": code, 
                "status": "error"
            }, 500
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query handling failed: {str(e)}")
    
    
@app.post("/setenv")
async def update_env(env: Environment):
    """
    Update the environment variables while preserving existing ones.
    Only modifies specified variables, leaving others unchanged.
    """
    try:
        print_info(f"Received environment updates: {list(env.keys())}")
        
        # Read existing environment variables
        existing_env = {}
        if os.path.exists(".env"):
            with open(".env", "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        try:
                            key, value = line.split('=', 1)
                            existing_env[key.strip()] = value.strip().replace("'", "")
                        except ValueError:
                            continue  # Skip malformed lines

        # Update with new values
        existing_env.update({
            key: str(value) for key, value in env.items() 
            if value is not None  # Only update non-None values
        })

        # Write back to file
        with open(".env", "w") as f:
            for key, value in existing_env.items():
                f.write(f"{key}='{value}'\n")

        # Reload environment variables
        load_dotenv(override=True)
        
        return {
            "message": f"Environment variables updated for {list(env.keys())}",
            "status": "success"
        }, 200
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Environment update failed: {str(e)}"
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8780)