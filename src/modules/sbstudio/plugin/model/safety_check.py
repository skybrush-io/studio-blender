from bpy.props import FloatProperty
from bpy.types import PropertyGroup

__all__ = ("SafetyCheckProperties",)


class SafetyCheckProperties(PropertyGroup):
    """Property group that stores the parameters and calculated values of the
    real-time flight safety checks.

    Some of the properties in this property group are calculated from the
    positions of the drones in the current frame and hence they are read-only
    to the user. Others represent parameters of the safety checks and hence
    they can be modified by the user.
    """

    min_distance = FloatProperty(
        name="Min distance",
        description="Minimum distance along all possible pairs of drones, calculated between their centers of mass",
        default=2.7,
        unit="LENGTH",
    )
