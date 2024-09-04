import os, sys

sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/..")

from utils.output_message_format.output_colour import print_info

class ServiceBase:
    """
    Base class for all services
    """
    def __init__(self):
        """
        prints a message when the service is started
        """
        print_info(f"Starting the {self.__class__.__name__} service...")