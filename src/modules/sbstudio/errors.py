__all__ = ("SkybrushStudioError",)


class SkybrushStudioError(RuntimeError):
    """Superclass for all exceptions thrown by Skybrush Studio."""

    def format_message(self) -> str:
        """Returns a user-friendly error message for this error."""
        return str(self)
