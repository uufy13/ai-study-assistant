"""Storage module exceptions."""


class StorageError(Exception):
    """Base exception for storage failures."""


class OutputDirectoryError(StorageError):
    """Raised when the output directory cannot be created."""


class WriteError(StorageError):
    """Raised when a file write operation fails."""
