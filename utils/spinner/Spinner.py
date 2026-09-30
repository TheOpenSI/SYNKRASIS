import threading
import time
import sys

from utils.output_message_format.output_colour import print_warning

class Spinner:
    """A text-based spinner animation for command-line interfaces."""
    
    def __init__(self, 
                 message="Loading...", 
                 chars_style: str = "block_building"):
        """
        Initialize the spinner.
        
        Args:
            message (str): The message to display alongside the spinner
            chars (list): Characters to use for the spinner animation
        """
        self.message = message
        self.chars = self._get_chars(chars_style)
        self.stop_event = threading.Event() # Control flag
        self.spinner_thread = None


    def _get_chars(self, chars_style: str):    
        if chars_style == "brail":
            return ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        elif chars_style == "dots":
            return ['.  ', '.. ', '...', ' ..', '  .', '   ']
        elif chars_style == "simple":
            return ['-', '\\', '|', '/']
        elif chars_style == "arrow":
            return ['←', '↖', '↑', '↗', '→', '↘', '↓', '↙']
        elif chars_style == "block_building":
            return [' ▏', ' ▎', ' ▍', ' ▌', ' ▋', ' ▊', ' ▉', ' █']
        elif chars_style == "bounce":
            return ['⠁', '⠂', '⠄', '⡀', '⢀', '⠠', '⠐', '⠈']
        elif chars_style == "pulse":
            return ['.', 'o', 'O', '@', '*']
        elif chars_style == "triangle":
            return ['◢', '◣', '◤', '◥']
        else:
            print_warning(f"Spinner style {chars_style} not found. Using simple style.")
            return self._get_chars("simple")
            
            
    def _spin(self):
        """The animation loop that runs in a separate thread."""
        i = 0
        max_len = max(len(char) for char in self.chars)
        
        while not self.stop_event.is_set():
            output = (self.chars[i % len(self.chars)] + 
                      " " * (max_len - len(self.chars[i % len(self.chars)])))
            print(f"{self.message} {output}", end="\r")
            i += 1
            time.sleep(0.2)
            

    def start(self):
        """Start the spinner animation in a background thread."""
        self.spinner_thread = threading.Thread(target=self._spin)
        self.spinner_thread.start()
        

    def stop(self):
        """Stop the spinner animation and clean up."""
        if self.spinner_thread:
            self.stop_event.set()
            self.spinner_thread.join()