from bpy.props import FloatProperty, IntProperty, StringProperty
from bpy.types import PropertyGroup

from sbstudio.plugin.constants import NUM_PYRO_CHANNELS

__all__ = ("PyroControlPanelProperties",)


class PyroControlPanelProperties(PropertyGroup):
    channel = IntProperty(
        name="Channel",
        description="The (1-based) channel index the pyro is attached to",
        default=1,
        min=1,
        max=NUM_PYRO_CHANNELS,
    )

    name = StringProperty(
        name="Name",
        description="Name of the pyro effect to trigger",
        default="30s Gold Glittering Gerb",
    )

    duration = FloatProperty(
        name="Duration",
        description="The duration of the pyro effect",
        default=30,
        min=0.1,
        unit="TIME",
        step=100,  # button step is 1/100th of step
    )

    prefire_time = FloatProperty(
        name="Prefire time",
        description="The time needed for the pyro effect to show up after it gets triggered",
        min=0,
        unit="TIME",
        step=100,  # button step is 1/100th of step
    )

    # TODO: add yaw and pitch angle relative to the drone, if needed
