# =============================================================================================
# SYNKRASIS Logger Utility
# This module provides a singleton logger class for service
# Usage:
#     debug(message)
#     info(message)
#     warning(message)
#     error(message)
#     critical(message)
#     exception(message)
#     quit()
# =============================================================================================
from __future__ import annotations

import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import logging
import logging.handlers
import os
from threading import Lock


class Logger:
    """
    Singleton logger class for service objects.
    Each service class gets one logger instance regardless of number of objects.
    """
    
    _instances = {}  # Dictionary to store one logger per service class
    _lock = Lock()
    
    def __new__(cls, 
                service_name: str, 
                log_level: str) -> Logger:
        """
        Ensure singleton pattern per service name
        Singleton does not care about log level, so 2 objects with same service name
        will share the same logger instance regardless of log level.
        
        Args:
            service_name: Name of the service to create or get logger for
        """
        if service_name not in cls._instances:
            with cls._lock:
                if service_name not in cls._instances: # In case another thread created it
                    instance = super().__new__(cls) # Object parent class
                    cls._instances[service_name] = instance
                    instance._initialised = False # Thread safety
        return cls._instances[service_name]


    def __init__(self, 
                 service_name: str,
                 log_level: str) -> None:
        """
        Initialise logger for the service if not already initialized
        
        Args:
            service_name: Name of the service to create logger for
            log_level: String representation of log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        if self._initialised:
            return
            
        self.service_name = service_name
        self.log_level = self._parse_log_level(log_level)
        self.logger = None
        self.handlers = []
        self._setup_logger()
        self._initialised = True
        
        
    def _parse_log_level(self, log_level: str) -> int:
        """
        Convert string log level to logging module constant
        
        Args:
            log_level: String representation of log level
            
        Returns:
            Integer constant from logging module
            
        Raises:
            ValueError: If log_level is not a valid logging level
        """
        level_mapping = {
            'DEBUG': logging.DEBUG,      # 10 - Most verbose
            'INFO': logging.INFO,        # 20 - General information
            'WARNING': logging.WARNING,  # 30 - Something unusual happened
            'ERROR': logging.ERROR,      # 40 - Something went wrong
            'CRITICAL': logging.CRITICAL # 50 - Severe problems
        }
        target_level = log_level.upper()

        if target_level not in level_mapping:
            valid_levels = ', '.join(level_mapping.keys())
            raise ValueError(f"Invalid log level '{log_level}'. Valid levels are: {valid_levels}")
        
        return level_mapping[target_level]
    
    
    def _setup_logger(self) -> None:
        """
        Set up the logger with rotating file handler
        """
        log_directory = 'service_logs'
        if not os.path.exists(log_directory):
            os.makedirs(log_directory)
        
        
        self.logger = logging.getLogger(f'Logger.{self.service_name}')
        self.logger.setLevel(self.log_level)
        
        # Prevent duplicate handlers if logger already exists
        if self.logger.handlers:
            return
        
        # Logging formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        
        # Set up rotating file handler (10MB max, keep 5 backups)
        log_filename = os.path.join(log_directory, f'{self.service_name}.log')
        rotating_handler = logging.handlers.RotatingFileHandler(
            log_filename,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        rotating_handler.setLevel(self.log_level)
        rotating_handler.setFormatter(formatter)
        
        # Add handler to logger and track it
        self.logger.addHandler(rotating_handler)
        self.handlers.append(rotating_handler)
        
        # Log that the logger has been initialized
        self.logger.info(f"Logger initialized for service: {self.service_name}")


    def debug(self, message: str) -> None:
        """Log debug message"""
        self.logger.debug(message)


    def info(self, message: str) -> None:
        """Log info message"""
        self.logger.info(message)


    def warning(self, message: str) -> None:
        """Log warning message"""
        self.logger.warning(message)


    def error(self, message: str) -> None:
        """Log error message"""
        self.logger.error(message)
    
    
    def critical(self, message: str) -> None:
        """Log critical message"""
        self.logger.critical(message)
    
    
    def exception(self, message: str) -> None:
        """Log exception with traceback"""
        self.logger.exception(message)
    
    
    def quit(self) -> None:
        """
        Clean up logger resources - close all handlers
        """
        if self.logger:
            for handler in self.handlers:
                handler.close()
                self.logger.removeHandler(handler)
            self.handlers.clear()
            self.logger.info(f"Logger cleanup completed for service: {self.service_name}")

# ===============================================================================================

# Test Generated by Claude
from services.Base import ServiceBase

class DatabaseService(ServiceBase):
    """Example service class using the logger"""
    
    def __init__(self):
        self.logger = Logger('DatabaseService', 'INFO')
        self.logger.info("DatabaseService instance created")
    
    def connect(self):
        self.logger.debug("Attempting database connection")
        try:
            self.logger.info("Database connection successful")
        except Exception as e:
            self.logger.error(f"Database connection failed: {e}")
            self.logger.exception("Full exception details:")
    
    def cleanup(self):
        self.logger.info("DatabaseService cleanup started")
        self.logger.quit()  # Clean up logger resources


class APIService(ServiceBase):
    """Another example service class using the logger"""
    
    def __init__(self):
        self.logger = Logger('APIService', 'INFO')
        self.logger.info("APIService instance created")
    
    def handle_request(self, request_id):
        self.logger.debug(f"Processing request: {request_id}")
        self.logger.info(f"Request {request_id} completed successfully")
    
    def cleanup(self):
        self.logger.info("APIService cleanup started")
        self.logger.quit()


if __name__ == "__main__":
    db1 = DatabaseService()
    db2 = DatabaseService()  # Will use the same logger instance
    
    api = APIService()  # Gets its own logger instance
    
    # Test logging
    db1.connect()
    db2.logger.warning("This warning comes from db2 but uses same logger as db1")
    api.handle_request("REQ-123")
    
    # Cleanup when done
    db1.cleanup()
    api.cleanup()