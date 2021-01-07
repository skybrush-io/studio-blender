from bpy.props import BoolProperty, FloatProperty
from bpy.types import PropertyGroup

from sbstudio.plugin.utils.bloom import set_bloom_effect_enabled


__all__ = ("DroneShowAddonFileSpecificSettings",)


def use_bloom_effect_updated(self, context):
    set_bloom_effect_enabled(self.use_bloom_effect)


class DroneShowAddonFileSpecificSettings(PropertyGroup):
    """Property group that stores the generic settings of a drone show in the
    addon that do not belong elsewhere.
    """

    max_acceleration = FloatProperty(
        name="Max acceleration",
        description="Maximum acceleration allowed when planning the duration of transitions between fixed points",
        default=4,
        unit="ACCELERATION",
        min=0.1,
        soft_min=0.1,
        soft_max=20,
    )

    use_bloom_effect = BoolProperty(
        name="Use bloom effect",
        description="Specifies whether the bloom effect should automatically be enabled on the 3D View when the show is loaded",
        default=True,
        update=use_bloom_effect_updated,
    )
