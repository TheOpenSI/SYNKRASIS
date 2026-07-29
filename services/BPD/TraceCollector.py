import sys, types
from typing import Any


class TraceCollector:

    def __init__(self):
        self.log: list[dict[str, Any]] = []


    def tracer(self, 
               frame: types.FrameType, 
               event: str, 
               arg: Any) -> types.TracebackType:
        """
        Traces function calls and records information about each call.

        Args:
            frame (types.FrameType): The current frame.
            event (str): The type of trace event. Tells us why the trace function was called.
                Options include 'call', 'line', 'return', 'exception', and 'c_call'.
            arg (Any): Additional argument for the trace event. e.g., for 'return' events, this is the return value.

        Returns:
            types.TracebackType: The traceback object.
        """
        self.log.append(
            {
                # "file_name" : frame.f_code.co_filename,
                "event" : event,
                "func" : frame.f_code.co_name,
                "line" : frame.f_lineno,
                "locals" : frame.f_locals.copy(),
                # "globals"   : frame.f_globals.copy(),
                "arg" : arg,
                # "parent_func" : frame.f_back.f_code.co_name if frame.f_back else None
            }
        )
        return self.tracer
        # return None


    def run(self, 
            func: callable, 
            *args, 
            **kwargs) -> tuple[Any, list[dict[str, Any]]]:
        """
        Runs a function with tracing enabled and collects trace logs.

        Args:
            func (callable): The function to run with tracing.

        Returns:
            tuple[Any, list[dict[str, Any]]]: A tuple containing the result of the function and the list of trace logs.
        """
        self.log = []
        sys.settrace(self.tracer)
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            result = e
        finally:
            sys.settrace(None)
        return result, self.log
