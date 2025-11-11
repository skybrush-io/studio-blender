from sbstudio.errors import SkybrushStudioError

__all__ = (
    "SkybrushStudioAddonError",
    "SkybrushStudioExportWarning",
    "SkybrushStudioTaskCancelledError",
    "StoryboardValidationError",
)


class SkybrushStudioAddonError(SkybrushStudioError):
    """Base class for all errors in this addon."""

    pass


class StoryboardValidationError(SkybrushStudioAddonError):
    """Error thrown when the validation of the storyboard has failed."""

    pass


class SkybrushStudioExportWarning(SkybrushStudioError):
    """Error thrown during an export operation when the export cannot be
    completed. Converted into a Blender warning.
    """

    pass


class SkybrushStudioTaskCancelledError(SkybrushStudioError):
    """Error thrown during a long lasting task that the user cancelled."""

    pass
