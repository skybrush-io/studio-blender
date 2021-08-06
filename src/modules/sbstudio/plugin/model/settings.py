from bpy.props import BoolProperty, EnumProperty, FloatProperty, PointerProperty
from bpy.types import Collection, PropertyGroup

from sbstudio.plugin.utils.bloom import set_bloom_effect_enabled


__all__ = ("DroneShowAddonFileSpecificSettings",)


def use_bloom_effect_updated(self, context):
    set_bloom_effect_enabled(self.use_bloom_effect)


class DroneShowAddonFileSpecificSettings(PropertyGroup):
    """Property group that stores the generic settings of a drone show in the
    addon that do not belong elsewhere.
    """

    drone_collection = PointerProperty(
        type=Collection,
        name="Drone collection",
        description="The collection that contains all the objects that are to be treated as drones",
    )

    max_acceleration = FloatProperty(
        name="Max acceleration",
        description="Maximum acceleration allowed when planning the duration of transitions between fixed points",
        default=4,
        unit="ACCELERATION",
        min=0.1,
        soft_min=0.1,
        soft_max=20,
    )

    show_type = EnumProperty(
        name="Show type",
        description="Specifies whether the drone show is an outdoor or an indoor show",
        default="OUTDOOR",
        items=[
            (
                "OUTDOOR",
                "Outdoor",
                "Outdoor show, for drones that navigate using a geodetic (GPS) coordinate system",
                1,
            ),
            (
                "INDOOR",
                "Indoor",
                "Indoor show, for drones that navigate using a local (XYZ) coordinate system",
                2,
            ),
        ],
    )

    use_bloom_effect = BoolProperty(
        name="Use bloom effect",
        description="Specifies whether the bloom effect should automatically be enabled on the 3D View when the show is loaded",
        default=True,
        update=use_bloom_effect_updated,
    )
