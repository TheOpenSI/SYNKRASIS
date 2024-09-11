import sys, os, gc
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from typing import List

from services.Base import ServiceBase
from utils.output_message_format.output_colour import print_info

def call_cleanup(services: List[ServiceBase] = None):
    print_info("Starting cleanup")
    if services is None:
        return
    for service in services:
        if service is None:
            continue
        service.cleanup()
        del service
        
    gc.collect()