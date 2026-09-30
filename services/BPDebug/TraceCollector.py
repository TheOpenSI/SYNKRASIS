import sys, types
from typing import Any


class TraceCollector:

    def __init__(self):
        self.log: list[dict[str, Any]] = []


    def tracer(self, 
               frame: types.FrameType, 
               event: str, 
               arg: Any) -> types.TracebackType | None:
        self.log.append(
            {
                "event"  : event,
                "func"   : frame.f_code.co_name,
                "line"   : frame.f_lineno,
                "locals" : frame.f_locals.copy(),
                "arg"    : arg
            }
        )
        return self.tracer


    def run(self, 
            func: callable, 
            *args, 
            **kwargs) -> tuple[Any, list[dict[str, Any]]]:
        self.log = []
        sys.settrace(self.tracer)
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            result = e
        finally:
            sys.settrace(None)
        return result, self.log
