import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/..")

from abc import ABC, abstractmethod

from utils.output_message_format.output_colour import print_info

class ServiceBase(ABC):
    """
    Base class for all services
    """
    def __init__(self):
        """
        prints a message when the service is started
        """
        print_info(f"Starting the {self.__class__.__name__} service...")
        
        
    @abstractmethod
    def cleanup(self):
        """
        Cleanup the service
        """
        pass