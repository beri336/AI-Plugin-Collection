# src/decorators.py

"""
Decorators for Ollama Manager.
  This module provides reusable decorators for common patterns like checking if Ollama is running, retry logic, and error handling.
"""

from typing import Callable, Any, TypeVar, Optional
from ollama_service import OllamaService as service

import functools
import logging
import time


# type variable for generic function signatures
F = TypeVar('F', bound=Callable[..., Any])

def require_running(func: F) -> F:
    """Decorator to check if Ollama is running before execution.
    
    Raises:
        RuntimeError: If Ollama is not running
        
    Usage:
        @require_running
        def list_models(self):
            #### No manual check needed
            ...
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if not service.is_process_running:
            raise RuntimeError('Ollama is not running!')
        
        return func(self, *args, **kwargs)
    
    return wrapper

def retry_on_failure(
    max_attempts: int=3,
    delay: float =1.0,
    backoff: float=2.0,
    exceptions: tuple=(Exception,)
):
    """Decorator to retry a function on failure.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each attempt
        exceptions: Tuple of exception types to catch
        
    Usage:
        @retry_on_failure(max_attempts=3, delay=1.0)
        def unstable_operation(self):
            ...
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            curr_delay = delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(self, *args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts -1:
                        time.sleep(curr_delay)
                        curr_delay += backoff
                    else:
                        raise last_exception
            
            # should never reach here (but for type safety)
            raise last_exception if last_exception else Exception('Retry failed.')
        
        return wrapper
    return decorator

def log_execution(logger: Optional[logging.Logger]=None):
    """Decorator to log function execution.
    
    Args:
        logger: Logger instance (uses default if None)
        
    Usage:
        @log_execution()
        def important_operation(self):
            ...
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            func_name = func.__name__
            _logger = logger or logging.getLogger(__name__)
            
            _logger.debug(f"Executing {(func_name)}")
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                _logger.debug(f"{func_name} completed in {elapsed:.2f}s")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                _logger.error(f"{func_name} failed after {elapsed:.2f}s: {e}")
                raise
        return wrapper
    return decorator

def cache_result(ttl_seconds: int=300):
    """Decorator to cache function results for a given time.
    
    Args:
        ttl_seconds: Time to live for cached result in seconds
        
    Usage:
        @cache_result(ttl_seconds=60)
        def expensive_operation(self):
            ...
    """
    
    def decorator(func: F) -> F:
        cache = {}
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # create a cache key form function name and arguments
            key = (func.__name__, args, tuple(sorted(kwargs.items())))
            current_time = time.time()
            
            # check if we have a valid cached result
            if key in cache:
                result, timestamp = cache[key]
                if current_time - timestamp < ttl_seconds:
                    return result
            
            # execute function and cache result
            result = func(*args, **kwargs)
            cache[key] = (result, current_time)
            return result
        return wrapper
    return decorator

def handle_exceptions(
    default_return: Any=None,
    log_error: bool=True,
    raise_on_error: bool=False
):
    """Decorator to handle exceptions gracefully.
    
    Args:
        default_return: Value to return on exception
        log_error: Whether to log the exception
        raise_on_error: Whether to re-raise the exception
        
    Usage:
        @handle_exceptions(default_return=[], log_error=True)
        def risky_operation(self):
            ...
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error in {func.__name__}: {e}")
                
                if raise_on_error:
                    raise
                
                return default_return
        
        return wrapper
    return decorator

def validate_model_name(func: F) -> F:
    """Decorator to validate model name parameter.
    
    Checks if 'model' parameter is a non-empty string.
    
    Raises:
        ValueError: If model name is invalid
        
    Usage:
        @validate_model_name
        def pull_model(self, model: str):
            ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # check if model is in args or kwargs
        model = None
        
        # try to get from kwargs first
        if 'model' in kwargs:
            model = kwargs['model']
        # then try positional args (assuming model is second arg after self)
        elif len(args) > 1:
            model = args[1]
        
        if not model or not isinstance(model, str) or not model.strip():
            raise ValueError("Model name must be a non-empty string")
        
        return func(*args, **kwargs)
    
    return wrapper

def timing(func: F) -> F:
    """Decorator to measure and print execution time.
    
    Usage:
        @timing
        def slow_operation(self):
            ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start_time
        print(f"{func.__name__} took {elapsed:.4f} seconds")
        return result
    
    return wrapper
