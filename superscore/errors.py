"""Custom Exceptions"""


class BackendError(Exception):
    """Raised when a Backend data operation fails"""
    pass


class EntryExistsError(BackendError):
    """Raised when an existing Entry is saved to the backend"""
    pass


class EntryNotFoundError(BackendError):
    """Raised when an Entry is fetched from the backend but can't be found"""
    pass


class CommunicationError(Exception):
    """Raised when communication with the control system fails"""
    pass
