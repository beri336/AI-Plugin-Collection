# src/core/decorators.py

'''
Decorators for Ollama API functions
  This module provides reusable decorators that encapsulate common cross-cutting tasks.

- @require_running: Checks whether the Ollama service is active before API calls
- @validate_model_name: Validates model parameters for non-emptiness
- @handle_exceptions: Catches exceptions with configurable behavior
- @retry_on_failure: Implements retry logic with exponential backoff
- @cache_result: Caches function results with configurable TTL
- @log_execution: Logs execution time and errors of functions
- @timing: Measures and outputs performance metrics
'''

from typing import TypeVar, Callable, Any, Optional

import functools
import logging
import time


# type variable for generic function signatures
F = TypeVar('F', bound=Callable[..., Any])

def require_running(func: F) -> F:
    """Decorator to ensure Ollama service is running before execution.
    
    Checks if the Ollama service is active and raises RuntimeError if not.
    Uses lazy import to avoid circular dependencies.
    
    Args:
        func: Function to decorate (must be a method with 'self')
        
    Returns:
        Wrapped function that checks service status before execution
    
    Raises:
        RuntimeError: If Ollama service is not running
    
    Note:
        This decorator expects the decorated function to be a method
        (having 'self' as first parameter).
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs) -> Any:
        # lazy import to avoid circular dependency
        from modules.service_manager import Service
        
        service = Service()
        if not service.is_running:
            raise RuntimeError('Ollama is not running!')
        
        return func(self, *args, **kwargs)
    
    return wrapper

def retry_on_failure(
    max_attempts: int=3,
    delay: float =1.0,
    backoff: float=2.0,
    exceptions: tuple=(Exception,)
):
    """Decorator to retry function execution on failure with exponential backoff.
    
    Retries the decorated function up to max_attempts times if it raises
    one of the specified exceptions. Uses exponential backoff between retries.
    
    Args:
        max_attempts: Maximum number of execution attempts (default: 3)
        delay: Initial delay between retries in seconds (default: 1.0)
        backoff: Delay increase factor after each retry (default: 2.0)
        exceptions: Tuple of exception types to catch and retry (default: (Exception,))
    
    Returns:
        Decorator function that wraps the target function
        
    Raises:
        Last caught exception if all retry attempts fail
    
    Note:
        Backoff is additive, not multiplicative. First retry waits 'delay',
        second waits 'delay + backoff', third waits 'delay + 2*backoff', etc.
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs) -> Any:
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
    """Decorator to log function execution time and errors.
    
    Logs function entry, successful completion with execution time,
    or failure with error details. Uses provided logger or creates
    a module-level logger.
    
    Args:
        logger: Optional custom logger instance. If None, uses module logger
        
    Returns:
        Decorator function that wraps the target function
    
    Note:
        Successful executions log at DEBUG level, failures at ERROR level.
        The decorator re-raises exceptions after logging them.
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs) -> Any:
            func_name = func.__name__
            _logger = logger or logging.getLogger(__name__)
            
            _logger.debug(f"Executing {(func_name)}")
            start_time = time.time()
            
            try:
                result = func(self, *args, **kwargs)
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
    """Decorator to cache function results with time-to-live expiration.
    
    Caches function results based on function name and arguments. Cached
    results expire after ttl_seconds. Cache is shared across all calls
    to the decorated function.
    
    Args:
        ttl_seconds: Time-to-live for cached results in seconds (default: 300)
        
    Returns:
        Decorator function that wraps the target function
    
    Warning:
        Cache is function-scoped, not instance-scoped. All instances share
        the same cache. Arguments must be hashable.
    """
    def decorator(func: F) -> F:
        cache = {}
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
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
    """Decorator to handle exceptions with configurable behavior.
    
    Catches all exceptions and provides configurable error handling:
    optional logging, optional re-raising, and default return value.
    
    Args:
        default_return: Value to return if exception occurs and not re-raised
        log_error: Whether to log caught exceptions (default: True)
        raise_on_error: Whether to re-raise exceptions after logging (default: False)
        
    Returns:
        Decorator function that wraps the target function
    
    Note:
        When raise_on_error=True, default_return is ignored since
        the exception is re-raised.
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
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
    """Decorator to validate model name parameter before execution.
    
    Checks that the 'model' parameter (either as kwarg or 
    second positional argument) is a non-empty string.
    
    Args:
        func: Function to decorate (must have 'model' parameter)
        
    Returns:
        Wrapped function that validates model name before execution
        
    Raises:
        ValueError: If model name is missing, empty, not a string, or whitespace-only
    
    Note:
        Assumes 'model' is either a keyword argument or the second positional
        argument (index 1, after 'self').
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
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
    """Decorator to measure and print function execution time.
    
    Uses high-precision performance counter to measure execution time
    and prints result to stdout. Useful for quick performance profiling.
    
    Args:
        func: Function to decorate
        
    Returns:
        Wrapped function that measures and prints execution time
    
    Note:
        Uses time.perf_counter() for more accurate timing than time.time().
        Output goes to stdout via print(), not logging.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start_time
        print(f"{func.__name__} took {elapsed:.4f} seconds")
        
        return result
    
    return wrapper
