import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import subprocess

from services.Base import ServiceBase
from utils.output_message_format.output_colour import print_error, print_info, print_success, print_warning, print_pycapsule

class Container(ServiceBase):
    def __init__(self, 
                 IMAGE_NAME: str = "synkrasis", 
                 container_name: str = "synkrasis_alpha"):
        """Container class for managing docker containers

        Args:
            IMAGE_NAME (str, optional): Default image name. Defaults to "synkrasis".
            container_name (str, optional): Default container name. Defaults to "synkrasis_alpha".
        """
        self.IMAGE_NAME = IMAGE_NAME
        self.CONTAINER_NAME = container_name
        self.MOUNT_DIR_PATH = os.path.abspath(__file__).replace("Container.py", "mount_dir")
        self._check_if_image_exists() # check if image exists


    def _check_if_image_exists(self):
        """
        Check if docker imahe exists, if not build from Dockerfile
        """
        images = subprocess.run(f"docker images | grep {self.IMAGE_NAME}", shell=True, capture_output=True, text=True)
        if images.stdout.strip() == "":
            print_warning("Image does not exist")
            print_info("Building image...")
            docker_file_path = os.path.abspath(__file__).replace("Container.py", "Dockerfile")
            subprocess.run(f"docker build -t {self.IMAGE_NAME} {docker_file_path}", shell=True)
            print_success("Image built")
        else:
            print_info("Image found")
    

    def _check_if_container_exists(self) -> bool:
        """
        Check if container exists
        Returns:
            bool: True if container exists, False otherwise
        """
        containers = subprocess.run(f"docker ps -a | grep {self.container_name}", shell=True, capture_output=True, text=True)
        if containers.stdout.strip() == "":
             print_warning("Container does not exist")
        else:
            print_success("Container found")

        return not containers.stdout.strip() == ""


    def _create_container(self): # TODO: add return type
            print_info("Creating container...")
            print_success("Container created")
            # Debug
            # response = subprocess.run(("docker run -it "
            #                            f"--name {self.container_name} "
            #                            f"--entrypoint /bin/bash "
            #                            f"-v {self.MOUNT_DIR_PATH}:/usr/src/app "
            #                            f"{self.IMAGE_NAME}"),
            #                            shell = True)
            
            # Create the container
            response = subprocess.run((f"docker run "
                                       f"--name {self.container_name} "
                                       f"-v {self.MOUNT_DIR_PATH}:/usr/src/app "
                                       f"{self.IMAGE_NAME}"), 
                                      shell=True, capture_output=True, text=True)
            
            return response
     
            
    def start_container(self): # TODO: add return type
        if self._check_if_container_exists():
            print_info("Starting container...")
            response = subprocess.run(f"docker start -i {self.container_name}", shell=True, capture_output=True, text=True)
        else:
            response = self._create_container()
        
        print_pycapsule(response.stdout)
        print_pycapsule(response.returncode, "exit-code")
        error_response = "No error" if response.stderr == "" else response.stderr
        print_pycapsule(error_response, "error-response")
        
        return response
    
    
    def cleanup(self):
        """Stop the container to free up resources"""
        container_running = subprocess.run(f"docker ps | grep {self.CONTAINER_NAME}", shell=True, capture_output=True, text=True)
        
        if container_running.stdout.strip() != "":
            # Stop the container if it is running
            subprocess.run(f"docker stop {self.CONTAINER_NAME}", shell=True, capture_output=True, text=True)
            
        print_success("Container resources cleaned up.")
        
       
