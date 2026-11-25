import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggest, Suggestion
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document


class CommandAutoSuggest(AutoSuggest):    
    def __init__(self, 
                 commands: list) -> None:
        """
        Command suggestion for CLI.

        Args:
            commands (dict): Available commands for suggestion.
        """
        self.commands = commands
    
    
    # abstractmethod
    def get_suggestion(self, 
                       buffer: Buffer, 
                       document: Document) -> Suggestion:
        text = document.text
        
        if not text.startswith('\\') or len(text) < 2:
            return None
        
        command_part = text[1:] # after the backslash
        matches = [cmd for cmd in self.commands if cmd.startswith(command_part)]
        
        if not matches:
            return None
        
        shortest = min(matches, key=len) # shortest match
        suggestion_text = shortest[len(command_part):]
        
        return Suggestion(suggestion_text)