from bpy.props import FloatVectorProperty

__all__ = ("ColorProperty",)


def ColorProperty(**kwds):
    """Factory function disguised as a class; creates a Blender property that
    is suitable for storing a color.
    """
    props = {"default": (1.0, 1.0, 1.0)}
    props.update(kwds)
    props.update(subtype="COLOR", min=0.0, max=1.0)
    return FloatVectorProperty(**props)
