"""Pipeline-level exceptions."""


class PipelineError(Exception):
    """Base class for all pipeline-related errors."""


class EmptyContentError(PipelineError):
    """Raised when a Document has no content to process."""
