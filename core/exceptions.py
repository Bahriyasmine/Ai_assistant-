"""
core/exceptions.py — custom exception types for the app.
Defined in one place so the API layer can map each to a specific HTTP
status and message instead of catching generic RuntimeError and guessing.
"""


class AssistantError(Exception):
    """Base for every custom exception in the app.
    Routes can catch this as a fallback to turn any app-level failure
    into a controlled HTTP response without leaking tracebacks.
    """


class MissingAPIKeyError(AssistantError):
    """OPENAI_API_KEY is not set in the environment.
    Server-side config problem -> HTTP 500.
    """


class VectorStoreNotConfiguredError(AssistantError):
    """No vector store has been created/persisted yet.
    Caller should run /setup/init first -> HTTP 503.
    """


class NoDataFilesError(AssistantError):
    """The data/ directory has no files to index.
    Setup cannot proceed -> HTTP 503.
    """
