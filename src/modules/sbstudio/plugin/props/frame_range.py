from bpy.props import EnumProperty
from bpy.types import Context

from typing import Optional, Tuple

from sbstudio.plugin.utils import with_context

__all__ = ("FrameRangeProperty",)


def FrameRangeProperty(**kwds):
    """Factory function disguised as a class; creates a Blender property that
    is suitable for selecting a typical frame range.
    """
    props = {
        "name": "Frame range",
        "description": "Choose a frame range to use for this operation",
        "items": (
            ("STORYBOARD", "Storyboard", "Use the storyboard to define frame range"),
            ("RENDER", "Render", "Use global render frame range set by scene"),
            ("PREVIEW", "Preview", "Use global preview frame range set by scene"),
            (
                "AROUND_CURRENT_FRAME",
                "Current formation or transition",
                "Use the formation or transition containing the current frame",
            ),
        ),
        "default": "STORYBOARD",
    }
    props.update(kwds)
    return EnumProperty(**props)


@with_context
def resolve_frame_range(
    range: str, *, context: Optional[Context] = None
) -> Optional[Tuple[int, int]]:
    """Resolves one of the commonly used frame ranges used in multiple places
    throughout the plugin.
    """
    assert context is not None  # it was injected

    if range == "RENDER":
        # Return the entire frame range of the current scene
        return (context.scene.frame_start, context.scene.frame_end)
    elif range == "PREVIEW":
        # Return the selected preview range of the current scene
        return (context.scene.frame_preview_start, context.scene.frame_preview_end)
    elif range == "STORYBOARD":
        # Return the frame range covered by the storyboard
        return (
            context.scene.skybrush.storyboard.frame_start,
            context.scene.skybrush.storyboard.frame_end,
        )
    elif range == "AROUND_CURRENT_FRAME":
        # Return the frame range covered by the formation or transition around
        # the current frame
        storyboard = context.scene.skybrush.storyboard
        return storyboard.get_frame_range_of_formation_or_transition_at_frame(
            context.scene.frame_current
        )
    else:
        raise RuntimeError(f"Unknown frame range: {range!r}")
