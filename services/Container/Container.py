# For the time being, the container will run the main.py file in the mount_dir when started.
# Will release a more general version soon to bypass the current entrypoint.

import os, sys, shutil
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import subprocess
import re

from services.Base import ServiceBase
from utils.output_message_format.output_colour import print_error, print_info, print_success, print_warning, print_pycapsule

class Container(ServiceBase):
    def __init__(self, 
                 image_name: str = "synkrasis",
                 container_name: str = "synkrasis_alpha"):
        """Container class for managing docker containers

        Args:
            IMAGE_NAME (str, optional): Default image name. Defaults to "synkrasis".
            container_name (str, optional): Default container name. Defaults to "synkrasis_alpha".
        """
        super().__init__()
        current_dir = os.path.dirname(__file__)
        self.IMAGE_NAME = image_name
        self.CONTAINER_NAME = container_name
        self.MOUNT_DIR_PATH = os.path.join(current_dir, "mount_dir", container_name)
        self._check_if_image_exists() # check if image exists

        # Create mount and container directory.
        os.makedirs(self.MOUNT_DIR_PATH, exist_ok=True)

        # Copy start.sh to self.MOUNT_DIR_PATH.
        start_path = os.path.join(current_dir, "mount_dir/start.sh")
        shutil.copyfile(start_path, os.path.join(self.MOUNT_DIR_PATH, "start.sh"))

        # Copy requirements.txt to self.MOUNT_DIR_PATH.
        requirement_path = os.path.join(current_dir, "mount_dir/requirements.txt")

        if os.path.exists(requirement_path):
            shutil.copyfile(requirement_path, os.path.join(self.MOUNT_DIR_PATH, "requirements.txt"))

    def _check_if_image_exists(self):
        """
        Check if docker imahe exists, if not build from Dockerfile
        """
        images = subprocess.run(f"docker images | grep {self.IMAGE_NAME}", shell=True, capture_output=True, text=True)
        if images.stdout.strip() == "":
            print_warning("Image does not exist")
            print_info("Building image...")
            docker_file_path = os.path.dirname(__file__)
            subprocess.run(f"docker build -t {self.IMAGE_NAME} {docker_file_path}", shell=True)
            print_success("Image built")
        else:
            print_success("Image found")
    

    def _check_if_container_exists(self) -> bool:
        """
        Check if container exists
        Returns:
            bool: True if container exists, False otherwise
        """
        containers = subprocess.run(f"docker ps -a | grep {self.CONTAINER_NAME}", shell=True, capture_output=True, text=True)
        if containers.stdout.strip() == "":
             print_warning("Container does not exist")
        else:
            print_success("Container found")

        return not containers.stdout.strip() == ""


    def _create_container(self) -> subprocess.CompletedProcess:
            print_info("Creating container...")
            print_success("Container created")
            # Debug
            # response = subprocess.run(("docker run -it "
            #                            f"--name {self.CONTAINER_NAME} "
            #                            f"--entrypoint /bin/bash "
            #                            f"-v {self.MOUNT_DIR_PATH}:/usr/src/app "
            #                            f"{self.IMAGE_NAME}"),
            #                            shell = True)
            
            # Create the container
            response = subprocess.run((f"docker run "
                                       f"--name {self.CONTAINER_NAME} "
                                       f"-v {self.MOUNT_DIR_PATH}:/usr/src/app "
                                       f"{self.IMAGE_NAME}"),
                                      shell=True, capture_output=True, text=True)
            
            return response
     
            
    def start_container(self) -> subprocess.CompletedProcess:
        if self._check_if_container_exists():
            print_info("Starting container...")
            response = subprocess.run(f"docker start -i {self.CONTAINER_NAME}", shell=True, capture_output=True, text=True)
        else:
            response = self._create_container()
        
        print_pycapsule(response.stdout)
        print_pycapsule(response.returncode, "exit-code")
        
        error_response = "No error" 
        if response.stderr != "":
            filtered_error_message = re.search(r"Traceback.*$", response.stderr, re.DOTALL)
            if filtered_error_message:
                error_response = filtered_error_message.group()
            else:
                error_response = response.stderr
        print_pycapsule(error_response, "error-response")
        
        return response
    
    
    def cleanup(self):
        """Stop the container to free up resources"""
        container_running = subprocess.run(f"docker ps | grep {self.CONTAINER_NAME}", shell=True, capture_output=True, text=True)
        
        if container_running.stdout.strip() != "":
            # Stop the container if it is running
            subprocess.run(f"docker stop {self.CONTAINER_NAME}", shell=True, capture_output=True, text=True)
            
        print_success("Container resources cleaned up.")