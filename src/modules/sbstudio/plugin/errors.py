__all__ = ("SkybrushStudioAddonError", "StoryboardValidationError")


class SkybrushStudioAddonError(RuntimeError):
    """Base class for all errors in this addon."""

    pass


class StoryboardValidationError(SkybrushStudioAddonError):
    """Error thrown when the validation of the storyboard has failed."""

    pass
