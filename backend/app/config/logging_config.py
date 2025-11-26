"""
Logging Configuration Module

Provides centralized logging configuration with file and console handlers.
"""

import logging
import os
import functools
import inspect
from logging.handlers import TimedRotatingFileHandler

# Define log format strings
FILE_FORMATTER = '%(asctime)s.%(msecs)03d | %(levelname)-7s | [PID:%(process)d/TID:%(thread)d] | %(filename)s.%(funcName)s:%(lineno)d | %(message)s'
CONSOLE_FORMATTER = '%(asctime)s.%(msecs)03d | \033[1m%(levelname)-7s\033[0m | [PID:%(process)d/TID:%(thread)d] | %(filename)s.%(funcName)s:%(lineno)d | \033[36m%(message)s\033[0m'


class LoggingConfig:
    """Logging configuration management"""
    
    def __init__(self, log_file_name='log', log_level=logging.INFO, backup_count=30, log_dir=None):
        self.log_file_name = log_file_name
        self.log_level = log_level
        self.backup_count = backup_count
        self.log_dir = log_dir
        self.logger = logging.getLogger()

    def setup_logging(self):
        """Setup logging with file and console handlers"""
        # Clear existing handlers to avoid duplicates
        self.logger.handlers.clear()
    
        self.logger.setLevel(self.log_level)

        # Get current script directory
        root_dir = os.path.dirname(os.path.abspath(__file__))

        # Use default directory if not specified
        if self.log_dir is None:
            self.log_dir = os.path.join(root_dir, "../../logs")

        # Create log directory if it doesn't exist
        try:
            os.makedirs(self.log_dir, exist_ok=True)
        except OSError as e:
            self.logger.error(f"Failed to create log directory {self.log_dir}: {e}")
            return self.logger

        # Create file handler with daily rotation
        file_formatter = logging.Formatter(FILE_FORMATTER)
        file_handler = TimedRotatingFileHandler(
            os.path.join(self.log_dir, f'{self.log_file_name}.log'),
            when='D',  # Daily rotation
            interval=1,
            backupCount=self.backup_count,
            encoding='utf-8',
        )
        file_handler.setFormatter(file_formatter)

        # Create console handler
        console_formatter = logging.Formatter(CONSOLE_FORMATTER)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)

        # Add handlers to logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        self.logger.info("Logging initialized successfully")
        # Prevent propagation to root logger
        self.logger.propagate = False
        return self.logger


def log_print(func):
    """Decorator for logging function calls and return values (supports sync/async)"""
    
    # Performance optimization: get parameter signature at decoration time
    try:
        sig = inspect.signature(func)
        param_names = list(sig.parameters.keys())
    except Exception:
        param_names = []
    
    def _safe_to_json(obj, max_length=500):
        """Safely convert object to JSON format"""
        import json
        from datetime import datetime, date
        from decimal import Decimal
        
        try:
            if obj is None or isinstance(obj, (bool, int, float, str)):
                result = str(obj)
                return result if len(result) <= max_length else result[:max_length] + "..."
            
            if isinstance(obj, bytes):
                return f"bytes(len={len(obj)})"
            
            class SafeEncoder(json.JSONEncoder):
                def default(self, o):
                    if isinstance(o, (datetime, date)):
                        return o.isoformat()
                    if isinstance(o, Decimal):
                        return float(o)
                    if hasattr(o, '__dict__'):
                        return o.__dict__
                    if hasattr(o, 'dict') and callable(o.dict):
                        return o.dict()
                    if hasattr(o, 'model_dump') and callable(o.model_dump):
                        return o.model_dump()
                    return f"<{type(o).__name__}>"
            
            json_str = json.dumps(obj, cls=SafeEncoder, ensure_ascii=False, indent=None)
            
            if len(json_str) > max_length:
                return json_str[:max_length] + "... (truncated)"

            return json_str
            
        except Exception:
            try:
                result = repr(obj)
                return result[:max_length] + "..." if len(result) > max_length else result
            except Exception:
                return f"<{type(obj).__name__} object (format_error)>"

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        logger = logging.getLogger(__name__)
        
        # Log parameters - skip first parameter (self/cls)
        params = []
        start_idx = 1 if args and hasattr(args[0], '__class__') else 0
        
        for i, arg in enumerate(args[start_idx:]):
            param_idx = start_idx + i
            if param_idx < len(param_names):
                param_name = param_names[param_idx]
                params.append(f"{param_name}={arg!r}")
            else:
                params.append(f"{arg!r}")
        
        params.extend(f"{k}={v!r}" for k, v in kwargs.items())
        
        args_str = ', '.join(params) if params else '(no args)'
        logger.info(f"[Call] {func.__qualname__} ←------------ Args: {args_str}")

        try:
            result = await func(*args, **kwargs)
            result_str = _safe_to_json(result)
            logger.info(f"[Return] {func.__qualname__} ------------→ Result: {result_str}")
            return result
        except Exception as e:
            logger.error(f"[Exception] {func.__qualname__} ! {e.__class__.__name__}: {str(e)}", exc_info=True)
            raise

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        logger = logging.getLogger(__name__)

        params = []
        start_idx = 1 if args and hasattr(args[0], '__class__') else 0
        
        for i, arg in enumerate(args[start_idx:]):
            param_idx = start_idx + i
            if param_idx < len(param_names):
                param_name = param_names[param_idx]
                params.append(f"{param_name}={arg!r}")
            else:
                params.append(f"{arg!r}")
        
        params.extend(f"{k}={v!r}" for k, v in kwargs.items())
        
        args_str = ', '.join(params) if params else '(no args)'
        logger.info(f"[Call] {func.__qualname__} ←------------ Args: {args_str}")

        try:
            result = func(*args, **kwargs)
            result_str = _safe_to_json(result)
            logger.info(f"[Return] {func.__qualname__} ------------→ Result: {result_str}")
            return result
        except Exception as e:
            logger.error(f"[Exception] {func.__qualname__} ! {e.__class__.__name__}: {str(e)}", exc_info=True)
            raise

    return async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper

