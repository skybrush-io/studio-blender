from sbstudio.errors import SkybrushStudioError

__all__ = ("SkybrushStudioAPIError",)


class SkybrushStudioAPIError(SkybrushStudioError):
    """Superclass for all errors related to the Skybrush Studio API."""

    pass


class NoOnlineAccessAllowedError(SkybrushStudioAPIError):
    """Error thrown when online access is explicitly disabled in Blender."""

    pass
