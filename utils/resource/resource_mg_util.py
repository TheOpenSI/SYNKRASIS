import sys, os, gc
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from typing import List

from Services.Base import ServiceBase

def call_cleanup(services: List[ServiceBase] = None):
    if services is None:
        return
    for service in services:
        service.cleanup()
        del servic
        
    gc.collect()