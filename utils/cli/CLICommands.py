import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

from utils.cli.CommandAutoSuggest import CommandAutoSuggest

class CLICommands:
    def __init__(self, 
                 commands: dict[str, callable] = None) -> None:
        self.commands = commands if commands is not None else {}
        self._add_default_commands()
        self.auto_suggest = CommandAutoSuggest(list(self.commands.keys()))
        

    def cmd_help(self) -> None:
        """
        Display available commands.
        """
        print("Available commands:")
        for cmd in self.commands.keys():
            print(f"  \\{cmd}")
        
    
    def cmd_exit(self) -> None:
        """
        Exit the CLI application.
        """
        exit_message = ("Goodbye! If you have any more questions or need assistance "
                        "in the future, feel free to return. Have a great day!")
        print(exit_message)
        sys.exit(0)
            
    
    def execute_command(self, command: str) -> None:
        """
        Execute the command if it exists.
        
        Args:
            command (str): The command string (with leading backslash).
        """
        cmd_name = command[1:]
        
        if cmd_name in self.commands:
            self.commands[cmd_name]()
        else:
            print(f"Unknown command: {command}")
            
    
    def _add_help_command(self) -> None:
        """
        Ensure 'help' command is available.
        """
        if "help" not in self.commands:
            self.commands["help"] = self.cmd_help
            
            
    def _add_exit_command(self) -> None:
        """
        Ensure 'exit' command is available.
        """
        if "exit" not in self.commands:
            self.commands["exit"] = self.cmd_exit
    
    
    def _add_default_commands(self) -> None:
        """
        Add default commands if not already present.
        """
        self._add_help_command()
        self._add_exit_command()