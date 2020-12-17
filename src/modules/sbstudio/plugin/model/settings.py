from bpy.props import BoolProperty
from bpy.types import PropertyGroup

from sbstudio.plugin.utils.bloom import set_bloom_effect_enabled


__all__ = ("DroneShowAddonSettings",)


def use_bloom_effect_updated(self, context):
    set_bloom_effect_enabled(self.use_bloom_effect)


class DroneShowAddonSettings(PropertyGroup):
    """Property group that stores the generic settings of a drone show in the
    addon that do not belong elsewhere.
    """

    use_bloom_effect = BoolProperty(
        name="Use bloom effect",
        description="Specifies whether the bloom effect should automatically be enabled on the 3D View when the show is loaded",
        default=True,
        update=use_bloom_effect_updated,
    )
