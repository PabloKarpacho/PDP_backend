class ServiceError(Exception):
    """Base class for service-layer errors."""


class ValidationError(ServiceError):
    """Raised when service input is invalid."""


class ForbiddenError(ServiceError):
    """Raised when the current user cannot access the requested resource."""


class NotFoundError(ServiceError):
    """Raised when the requested resource does not exist."""


class ConflictError(ServiceError):
    """Raised when a business rule prevents the requested action."""
