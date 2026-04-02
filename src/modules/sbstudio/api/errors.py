from sbstudio.api.constants import MINIMUM_BACKEND_VERSION
from sbstudio.api.types import Version
from sbstudio.errors import SkybrushStudioError

__all__ = ("SkybrushStudioAPIError",)


class SkybrushStudioAPIError(SkybrushStudioError):
    """Superclass for all errors related to the Skybrush Studio API."""

    def format_message(self) -> str:
        """Returns a user-friendly error message for this error."""
        return str(self)


class NoOnlineAccessAllowedError(SkybrushStudioAPIError):
    """Error thrown when online access is explicitly disabled in Blender."""

    def format_message(self) -> str:
        return (
            "Access of online resources is disabled in the Blender "
            + "preferences. Please enable online access and then try again."
        )


class BackendVersionMismatchError(SkybrushStudioAPIError):
    """Error thrown when the backend version is older than the expected
    minimum version.
    """

    def __init__(
        self,
        backend_version: Version | None = None,
        *,
        minimum_version: Version = MINIMUM_BACKEND_VERSION,
    ):
        self.backend_version = backend_version
        self.minimum_version = minimum_version

    def format_message(self) -> str:
        if self.backend_version:
            return (
                f"Skybrush Studio Server is outdated ({self.backend_version}). "
                f"Please update to {self.minimum_version} or above."
            )
        else:
            return (
                f"Skybrush Studio Server is outdated. "
                f"Please update to {self.minimum_version} or above."
            )
