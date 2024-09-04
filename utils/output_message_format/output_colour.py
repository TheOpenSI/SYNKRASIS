# This file contains the functions to print the output messages in different colours.
# the functions 
# - print_info -- green
# - print_warning --yellow
# - print_error --red 
# - print_model_output --blue
# are used to print the output messages in differrnt colours.
# refer to the Enums in the colour.py file to see the different colours available.
# ---------------------------------------------------------------------------------------

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.output_message_format.colour import Colour

def print_info(to_print:str):
    print(f"{Colour.GREEN.value}[INFO]{Colour.RESET.value} {to_print}")


def print_warning(to_print:str):
    print(f"{Colour.YELLOW.value}[WARNING]{Colour.RESET.value} {to_print}")


def print_error(to_print:str):
    print(f"{Colour.RED.value}[ERROR]{Colour.RESET.value} {to_print}")

def print_model_output(to_print:str, model_name:str):
    """
    model_name: str, repo of the model # TODO: more specific
    """
    print(f"{Colour.BLUE.value}[{model_name.split('/')[0].upper()}]{Colour.RESET.value} {to_print}")