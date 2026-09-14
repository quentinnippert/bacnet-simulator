"""Errors whose meaning is shared by application and adapters."""


class ValidationError(ValueError):
    pass


class NotFoundError(ValueError):
    pass


class ConflictError(RuntimeError):
    pass


class UnavailableError(RuntimeError):
    pass
