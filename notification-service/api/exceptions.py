"""
Custom exception handlers for the notification service API.
"""
import logging
from rest_framework.views import exception_handler


logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides consistent error responses.
    
    Returns:
        Response: Standardized error response
    """
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)
    
    if response is not None:
        # Log the exception
        logger.error(
            "API exception occurred",
            extra={
                'exception_type': type(exc).__name__,
                'exception_message': str(exc),
                'view': context.get('view').__class__.__name__ if context.get('view') else 'Unknown',
                'request_method': context.get('request').method if context.get('request') else 'Unknown',
                'request_path': context.get('request').path if context.get('request') else 'Unknown',
                'status_code': response.status_code,
            },
            exc_info=True
        )
        
        # Customize the response data
        custom_response_data = {
            'error': {
                'code': response.status_code,
                'message': _get_error_message(exc, response),
                'details': response.data if isinstance(response.data, dict) else {'detail': response.data},
                'timestamp': context.get('request').META.get('HTTP_X_REQUEST_ID') if context.get('request') else None
            }
        }
        
        response.data = custom_response_data
    
    return response


def _get_error_message(exc, response):
    """
    Get a user-friendly error message based on the exception type.
    
    Args:
        exc: The exception instance
        response: The DRF response object
        
    Returns:
        str: User-friendly error message
    """
    if hasattr(exc, 'detail'):
        if isinstance(exc.detail, dict):
            # For field validation errors, return the first error message
            for field, errors in exc.detail.items():
                if isinstance(errors, list) and errors:
                    return f"{field}: {errors[0]}"
                return f"{field}: {errors}"
        elif isinstance(exc.detail, list) and exc.detail:
            return str(exc.detail[0])
        else:
            return str(exc.detail)
    
    # Default messages based on status code
    status_messages = {
        400: "Bad request. Please check your input data.",
        401: "Authentication required.",
        403: "You don't have permission to perform this action.",
        404: "The requested resource was not found.",
        405: "Method not allowed.",
        409: "Conflict. The resource already exists or cannot be modified.",
        422: "Validation error. Please check your input data.",
        429: "Too many requests. Please slow down.",
        500: "Internal server error. Please try again later.",
        502: "Bad gateway. Service temporarily unavailable.",
        503: "Service unavailable. Please try again later.",
    }
    
    return status_messages.get(response.status_code, "An error occurred.")