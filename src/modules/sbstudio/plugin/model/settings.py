from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
)
from bpy.types import Collection, PropertyGroup

from sbstudio.math.rng import RandomSequence
from sbstudio.plugin.constants import RANDOM_SEED_MAX
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

    random_seed = IntProperty(
        name="Random seed",
        description="Root random seed value used to generate randomized stuff in this show file",
        default=0,
        min=1,
        soft_min=1,
        soft_max=RANDOM_SEED_MAX,
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

    @property
    def random_sequence_root(self) -> RandomSequence:
        """Returns a random sequence generated from the random seed associated
        to the project.

        Do not hold on to a reference to the random sequence returned from this
        property permanently; when the user changes the random seed, the old
        instance will not be invalidated, and neither will any random sequence
        that was forked off from it.
        """
        result = getattr(self, "_random_sequence_root", None)
        if result is None:
            self._random_sequence_root = RandomSequence(seed=self.random_seed)
        return self._random_sequence_root
