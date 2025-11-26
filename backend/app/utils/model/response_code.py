"""
Response Status Codes

Defines standard HTTP response status codes for the API.
"""


class ResponseCode:
    """Standard response status codes"""
    
    # Success codes (2xx)
    SUCCESS = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    
    # Client error codes (4xx)
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    TOO_MANY_REQUESTS = 429
    
    # Server error codes (5xx)
    INTERNAL_SERVER_ERROR = 500
    NOT_IMPLEMENTED = 501
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504
    
    # Custom business codes (1xxx)
    BUSINESS_ERROR = 1000
    VALIDATION_ERROR = 1001
    AUTHENTICATION_ERROR = 1002
    AUTHORIZATION_ERROR = 1003
    RESOURCE_NOT_FOUND = 1004
    DUPLICATE_RESOURCE = 1005
    
    @classmethod
    def get_message(cls, code: int) -> str:
        """Get default message for status code"""
        messages = {
            cls.SUCCESS: "Success",
            cls.CREATED: "Created successfully",
            cls.ACCEPTED: "Request accepted",
            cls.NO_CONTENT: "No content",
            
            cls.BAD_REQUEST: "Bad request",
            cls.UNAUTHORIZED: "Unauthorized",
            cls.FORBIDDEN: "Forbidden",
            cls.NOT_FOUND: "Resource not found",
            cls.METHOD_NOT_ALLOWED: "Method not allowed",
            cls.CONFLICT: "Resource conflict",
            cls.UNPROCESSABLE_ENTITY: "Validation failed",
            cls.TOO_MANY_REQUESTS: "Too many requests",
            
            cls.INTERNAL_SERVER_ERROR: "Internal server error",
            cls.NOT_IMPLEMENTED: "Not implemented",
            cls.BAD_GATEWAY: "Bad gateway",
            cls.SERVICE_UNAVAILABLE: "Service unavailable",
            cls.GATEWAY_TIMEOUT: "Gateway timeout",
            
            cls.BUSINESS_ERROR: "Business logic error",
            cls.VALIDATION_ERROR: "Validation error",
            cls.AUTHENTICATION_ERROR: "Authentication failed",
            cls.AUTHORIZATION_ERROR: "Authorization failed",
            cls.RESOURCE_NOT_FOUND: "Resource not found",
            cls.DUPLICATE_RESOURCE: "Resource already exists",
        }
        return messages.get(code, "Unknown error")


