from sbstudio.errors import SkybrushStudioError

__all__ = ("SkybrushStudioAddonError", "StoryboardValidationError")


class SkybrushStudioAddonError(SkybrushStudioError):
    """Base class for all errors in this addon."""

    pass


class StoryboardValidationError(SkybrushStudioAddonError):
    """Error thrown when the validation of the storyboard has failed."""

    pass
