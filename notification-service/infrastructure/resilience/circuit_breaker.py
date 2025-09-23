"""
Circuit breaker pattern implementation for resilient external service calls.
"""
import logging
import time
from enum import Enum
from typing import Callable, Any, Optional
from dataclasses import dataclass
from threading import Lock

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5
    timeout: int = 60  # seconds
    half_open_attempts: int = 3
    success_threshold: int = 2  # successes needed to close from half-open


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """
    Circuit breaker implementation to prevent cascading failures.
    """
    
    def __init__(self, config: CircuitBreakerConfig, name: str = "default"):
        self.config = config
        self.name = name
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.lock = Lock()
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with circuit breaker protection.
        """
        with self.lock:
            current_time = time.time()
            
            if self.state == CircuitBreakerState.OPEN:
                if current_time - self.last_failure_time >= self.config.timeout:
                    self.state = CircuitBreakerState.HALF_OPEN
                    self.success_count = 0
                    logger.info(f"Circuit breaker '{self.name}' moved to HALF_OPEN")
                else:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker '{self.name}' is OPEN. "
                        f"Retry after {self.config.timeout - (current_time - self.last_failure_time):.1f} seconds"
                    )
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
                
            except Exception as e:
                self._on_failure(current_time)
                raise e
    
    def _on_success(self):
        """Handle successful call."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                logger.info(f"Circuit breaker '{self.name}' CLOSED after successful recovery")
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = 0
    
    def _on_failure(self, current_time: float):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = current_time
        
        if self.state == CircuitBreakerState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                logger.warning(f"Circuit breaker '{self.name}' OPENED after {self.failure_count} failures")
        elif self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            logger.warning(f"Circuit breaker '{self.name}' returned to OPEN state")
    
    def get_state(self) -> dict:
        """Get current circuit breaker state."""
        return {
            'name': self.name,
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'last_failure_time': self.last_failure_time
        }


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""
    
    def __init__(self):
        self._breakers = {}
        self._lock = Lock()
    
    def get_breaker(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """Get or create a circuit breaker."""
        with self._lock:
            if name not in self._breakers:
                if config is None:
                    config = CircuitBreakerConfig()
                self._breakers[name] = CircuitBreaker(config, name)
            return self._breakers[name]
    
    def get_all_states(self) -> dict:
        """Get states of all circuit breakers."""
        return {name: breaker.get_state() for name, breaker in self._breakers.items()}


# Global registry instance
circuit_breaker_registry = CircuitBreakerRegistry()


def circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None):
    """
    Decorator to apply circuit breaker protection to a function.
    """
    def decorator(func: Callable) -> Callable:
        breaker = circuit_breaker_registry.get_breaker(name, config)
        
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        wrapper.circuit_breaker = breaker
        return wrapper
    
    return decorator