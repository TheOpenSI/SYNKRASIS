import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def wrap_text(text: str, 
              max_line_length: int=80):
    """
    Wrap text while preserving existing line breaks and only adding new line breaks
    when a line exceeds the maximum line length.
    
    Args:
        text (str): The input text to wrap
        max_line_length (int): Maximum characters per line
        
    Returns:
        str: The wrapped text
    """
    # Split the text into lines (preserving original line breaks)
    lines = text.split('\n')
    result = []
    
    for line in lines:
        # If the line is shorter than max_line_length, keep it as is
        if len(line) <= max_line_length:
            result.append(line)
        else:
            # Process longer lines
            current_line = ""
            words = line.split(' ')
            
            for word in words:
                # Check if adding this word would exceed the max length
                if len(current_line) + len(word) + 1 <= max_line_length:
                    # Add word with space
                    if current_line:
                        current_line += " " + word
                    else:
                        current_line = word
                else:
                    # Line would be too long, add current line to result and start a new line
                    result.append(current_line)
                    current_line = word
            
            # Last line
            if current_line:
                result.append(current_line)
    
    # Join all lines with \n
    return '\n'.join(result)