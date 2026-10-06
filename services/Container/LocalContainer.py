# =============================================================================
# LocalContainer - drop in replacement for Container that needs no docker.
# Runs main.py from the mount directory in a local subprocess.
# NOTE: There is NO sandboxing, only use it with trusted/low risk code for local testing.
# Usage:
#     - LocalContainer(mount_dir_name: str = "synk_local_mount",
#                      timeout: int = 600,
#                      python_executable: str = sys.executable)
#
#     - start_container()
#     - cleanup()
# =============================================================================

import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import subprocess

from services.Base import ServiceBase
from utils.output_message_format.output_colour import print_pycapsule


class LocalContainer(ServiceBase):
    TIMEOUT_RETURN_CODE = 124

    def __init__(self,
                 mount_dir_name: str = "synk_local_mount",
                 timeout: int = 600,
                 python_executable: str = sys.executable) -> None:
        """
        Args:
            mount_dir_name (str, optional): Mount directory name inside services/Container/mount_dir.
            timeout (int, optional): Timeout in seconds for a single main.py run. Defaults to 600.
            python_executable (str, optional): Python used to run main.py. Defaults to the current one.
        """
        super().__init__()
        self.MOUNT_DIR_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                           "mount_dir",
                                           mount_dir_name)
        self.timeout = timeout
        self.python_executable = python_executable
        os.makedirs(self.MOUNT_DIR_PATH, exist_ok=True)


    def start_container(self) -> subprocess.CompletedProcess:
        main_py_path = os.path.join(self.MOUNT_DIR_PATH, "main.py")
        command = [self.python_executable, main_py_path]

        if not os.path.exists(main_py_path):
            response = subprocess.CompletedProcess(command, 0, stdout="Nothing to execute", stderr="")
        else:
            try:
                response = subprocess.run(command,
                                          cwd=self.MOUNT_DIR_PATH,
                                          capture_output=True,
                                          text=True,
                                          timeout=self.timeout)
            except subprocess.TimeoutExpired as e:
                response = subprocess.CompletedProcess(
                    command,
                    self.TIMEOUT_RETURN_CODE,
                    stdout=self._to_text(e.stdout),
                    stderr=f"Exception: Generated code is running infinite loop (exceeded {self.timeout}s).")

        print_pycapsule(response.stdout)
        print_pycapsule(str(response.returncode), "exit-code")
        print_pycapsule("No error" if response.stderr == "" else response.stderr, "error-response")

        return response


    def _to_text(self, output) -> str:
        if output is None:
            return ""
        return output.decode(errors="replace") if isinstance(output, bytes) else output


    def cleanup(self):
        """Nothing is kept running, kept to match the Container interface."""
        pass
