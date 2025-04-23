from bpy.props import IntProperty, StringProperty
from bpy.types import PropertyGroup

from sbstudio.plugin.constants import NUM_PYRO_CHANNELS

__all__ = ("PyroControlPanelProperties",)


class PyroControlPanelProperties(PropertyGroup):
    name = StringProperty(
        name="Name",
        description="Unique descriptor of the pyro effect to trigger, in VDL format",
        default="30s Gold Glittering Gerb",
    )

    channel = IntProperty(
        name="Channel",
        description="The channel index the pyro is attached to",
        default=1,
        min=1,
        max=NUM_PYRO_CHANNELS,
    )

    # TODO: add yaw and pitch angle relative to the drone

    # TODO: parse duration of pyro effect from name or from some predefined database
