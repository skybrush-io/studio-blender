from bpy.props import EnumProperty

__all__ = ("FrameRangeProperty",)


def FrameRangeProperty(**kwds):
    """Factory function disguised as a class; creates a Blender property that
    is suitable for selecting a typical frame range.
    """
    props = dict(
        name="Frame range",
        description="Choose a frame range to use for this operation",
        items=(
            ("STORYBOARD", "Storyboard", "Use the storyboard to define frame range"),
            ("RENDER", "Render", "Use global render frame range set by scene"),
            ("PREVIEW", "Preview", "Use global preview frame range set by scene"),
        ),
        default="STORYBOARD",
    )
    props.update(kwds)
    return EnumProperty(**props)
