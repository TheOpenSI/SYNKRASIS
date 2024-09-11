# testing subprocess

import subprocess

class Sandbox:
    def __init__(self, terminal_name: str = "gnome-terminal"):
        self.terminal_app = terminal_name
        self.program = "python3"

    def run_code(self, file_name: str) -> str:
        result = subprocess.run(f"{self.program} {file_name}", shell = True, capture_output = True, text = True)
        return result.stdout.strip()

    @staticmethod
    def run_command(command: str = "whoami") -> str:
        """
        this is a test function
        :return: nothing, will only run the command whoami by default
        """
        # subprocess.run([self.terminal_app, "--", "bash", "-c", f"{command}; exec bash"])
        # subprocess.run([self.terminal_app, "--", "bash", "-c", command])
        # subprocess.run('ls -l', shell=True)

        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout.strip()