"""
Retry pattern implementation with exponential backoff.
"""
import logging
import random
import time
from typing import Callable, Any, Type, Tuple
from dataclasses import dataclass
from functools import wraps

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    backoff_factor: float = 2.0
    max_delay: float = 30.0
    min_delay: float = 1.0
    jitter: bool = True
    exponential: bool = True


class RetryExhaustedError(Exception):
    """Exception raised when all retry attempts are exhausted."""
    pass


class RetryHandler:
    """Handler for retry logic with exponential backoff."""
    
    def __init__(self, config: RetryConfig):
        self.config = config
    
    def execute(
        self, 
        func: Callable, 
        *args, 
        retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
        **kwargs
    ) -> Any:
        """
        Execute a function with retry logic.
        
        Args:
            func: Function to execute
            *args: Function arguments
            retryable_exceptions: Tuple of exception types that should trigger a retry
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            RetryExhaustedError: When all retry attempts are exhausted
        """
        last_exception = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                result = func(*args, **kwargs)
                if attempt > 1:
                    logger.info(f"Function succeeded on attempt {attempt}")
                return result
                
            except retryable_exceptions as e:
                last_exception = e
                
                if attempt == self.config.max_attempts:
                    logger.error(f"All {self.config.max_attempts} retry attempts exhausted")
                    break
                
                delay = self._calculate_delay(attempt)
                logger.warning(
                    f"Attempt {attempt} failed: {e}. Retrying in {delay:.2f} seconds..."
                )
                time.sleep(delay)
            
            except Exception as e:
                # Non-retryable exception
                logger.error(f"Non-retryable exception occurred: {e}")
                raise e
        
        raise RetryExhaustedError(
            f"Failed after {self.config.max_attempts} attempts. Last error: {last_exception}"
        ) from last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for the given attempt number."""
        if self.config.exponential:
            delay = self.config.min_delay * (self.config.backoff_factor ** (attempt - 1))
        else:
            delay = self.config.min_delay * self.config.backoff_factor
        
        # Apply maximum delay limit
        delay = min(delay, self.config.max_delay)
        
        # Add jitter to prevent thundering herd
        if self.config.jitter:
            jitter_factor = random.uniform(0.5, 1.5)
            delay *= jitter_factor
        
        return max(delay, 0.1)  # Minimum 100ms delay


def retry(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    max_delay: float = 30.0,
    min_delay: float = 1.0,
    jitter: bool = True,
    exponential: bool = True,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Decorator to add retry functionality to a function.
    
    Args:
        max_attempts: Maximum number of retry attempts
        backoff_factor: Multiplier for exponential backoff
        max_delay: Maximum delay between retries (seconds)
        min_delay: Minimum delay between retries (seconds)
        jitter: Whether to add random jitter to delays
        exponential: Whether to use exponential backoff
        retryable_exceptions: Tuple of exception types that should trigger a retry
    """
    def decorator(func: Callable) -> Callable:
        config = RetryConfig(
            max_attempts=max_attempts,
            backoff_factor=backoff_factor,
            max_delay=max_delay,
            min_delay=min_delay,
            jitter=jitter,
            exponential=exponential
        )
        retry_handler = RetryHandler(config)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return retry_handler.execute(
                func, *args, retryable_exceptions=retryable_exceptions, **kwargs
            )
        
        wrapper.retry_config = config
        wrapper.retry_handler = retry_handler
        return wrapper
    
    return decorator


class AsyncRetryHandler:
    """Async version of retry handler."""
    
    def __init__(self, config: RetryConfig):
        self.config = config
    
    async def execute(
        self, 
        func: Callable, 
        *args, 
        retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
        **kwargs
    ) -> Any:
        """Async version of retry execution."""
        import asyncio
        
        last_exception = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                if attempt > 1:
                    logger.info(f"Async function succeeded on attempt {attempt}")
                return result
                
            except retryable_exceptions as e:
                last_exception = e
                
                if attempt == self.config.max_attempts:
                    logger.error(f"All {self.config.max_attempts} async retry attempts exhausted")
                    break
                
                delay = self._calculate_delay(attempt)
                logger.warning(
                    f"Async attempt {attempt} failed: {e}. Retrying in {delay:.2f} seconds..."
                )
                await asyncio.sleep(delay)
            
            except Exception as e:
                logger.error(f"Non-retryable async exception occurred: {e}")
                raise e
        
        raise RetryExhaustedError(
            f"Async failed after {self.config.max_attempts} attempts. Last error: {last_exception}"
        ) from last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for the given attempt number."""
        if self.config.exponential:
            delay = self.config.min_delay * (self.config.backoff_factor ** (attempt - 1))
        else:
            delay = self.config.min_delay * self.config.backoff_factor
        
        delay = min(delay, self.config.max_delay)
        
        if self.config.jitter:
            jitter_factor = random.uniform(0.5, 1.5)
            delay *= jitter_factor
        
        return max(delay, 0.1)


def async_retry(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    max_delay: float = 30.0,
    min_delay: float = 1.0,
    jitter: bool = True,
    exponential: bool = True,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """Async decorator for retry functionality."""
    def decorator(func: Callable) -> Callable:
        config = RetryConfig(
            max_attempts=max_attempts,
            backoff_factor=backoff_factor,
            max_delay=max_delay,
            min_delay=min_delay,
            jitter=jitter,
            exponential=exponential
        )
        retry_handler = AsyncRetryHandler(config)
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_handler.execute(
                func, *args, retryable_exceptions=retryable_exceptions, **kwargs
            )
        
        wrapper.retry_config = config
        wrapper.retry_handler = retry_handler
        return wrapper
    
    return decorator