from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import Collection, PropertyGroup

from sbstudio.math.rng import RandomSequence
from sbstudio.plugin.constants import (
    DEFAULT_INDOOR_DRONE_RADIUS,
    DEFAULT_OUTDOOR_DRONE_RADIUS,
    DEFAULT_EMISSION_STRENGTH,
    RANDOM_SEED_MAX,
)
from sbstudio.plugin.utils.bloom import (
    set_bloom_effect_enabled,
    update_emission_strength,
)
from sbstudio.plugin.utils.gps_coordinates import (
    format_latitude,
    format_longitude,
    parse_latitude,
    parse_longitude,
)


__all__ = ("DroneShowAddonFileSpecificSettings",)

_drone_radius_updated_by_user: bool = False
"""Shows whether the drone radius has been updated by the user already."""

_latitude_updated_by_user: bool = False
"""Shows whether the latitude property has been updated by the user."""

_longitude_updated_by_user: bool = False
"""Shows whether the longitude property has been updated by the user."""


def use_bloom_effect_updated(self, context):
    set_bloom_effect_enabled(self.use_bloom_effect)


def emission_strength_updated(self, context):
    update_emission_strength(self.emission_strength)


def latitude_of_show_origin_updated(self, context):
    global _latitude_updated_by_user

    _latitude_updated_by_user = not _latitude_updated_by_user
    if _latitude_updated_by_user:
        latitude = parse_latitude(self.latitude_of_show_origin)
        self.latitude_of_show_origin = format_latitude(latitude)


def longitude_of_show_origin_updated(self, context):
    global _longitude_updated_by_user

    _longitude_updated_by_user = not _longitude_updated_by_user
    if _longitude_updated_by_user:
        longitude = parse_longitude(self.longitude_of_show_origin)
        self.longitude_of_show_origin = format_longitude(longitude)


def show_type_updated(self, context):
    """Called when the show type is updated by the user."""
    global _drone_radius_updated_by_user

    if not _drone_radius_updated_by_user:
        if self.show_type == "INDOOR":
            self.drone_radius = DEFAULT_INDOOR_DRONE_RADIUS
        else:
            self.drone_radius = DEFAULT_OUTDOOR_DRONE_RADIUS
        # need to set it back to False after previous updates
        _drone_radius_updated_by_user = False


def drone_radius_updated(self, context):
    """Called when the drone radius is updated by the user."""
    global _drone_radius_updated_by_user

    _drone_radius_updated_by_user = True


class DroneShowAddonFileSpecificSettings(PropertyGroup):
    """Property group that stores the generic settings of a drone show in the
    addon that do not belong elsewhere.
    """

    drone_collection = PointerProperty(
        type=Collection,
        name="Drone collection",
        description="The collection that contains all the objects that are to be treated as drones",
    )

    drone_radius = FloatProperty(
        name="Drone radius",
        description="The radius of the drone template to create.",
        default=DEFAULT_OUTDOOR_DRONE_RADIUS,
        unit="LENGTH",
        soft_min=0.1,
        soft_max=1,
        update=drone_radius_updated,
    )

    drone_template = EnumProperty(
        items=[
            ("SPHERE", "Sphere", "", 1),
            ("CONE", "Cone", "", 2),
            ("SELECTED", "Selected Object", "", 3),
        ],
        name="Drone template",
        description=(
            "Drone template object to use for all drones. "
            "The SPHERE is the default simplest isotropic drone object, "
            "the CONE is anisotropic for visualizing yaw control, "
            "or use SELECTED for any custom object that is selected right now."
        ),
        default="SPHERE",
        options=set(),
    )

    # Note that Blender does not have enough floating point precision for lat/lon,
    # so we store them as strings and validate in a custom update function

    latitude_of_show_origin = StringProperty(
        name="Latitude of show origin",
        description="Proposed latitude of the origin of the show coordinate system, in degrees",
        default="N0.0",
        update=latitude_of_show_origin_updated,
    )

    longitude_of_show_origin = StringProperty(
        name="Longitude of show origin",
        description="Proposed longitude of the origin of the show coordinate system, in degrees",
        default="E0.0",
        update=longitude_of_show_origin_updated,
    )

    max_acceleration = FloatProperty(
        name="Preferred acceleration",
        description="Preferred acceleration for drones when planning the duration of transitions between fixed points",
        default=4,
        unit="ACCELERATION",
        min=0.1,
        soft_min=0.1,
        soft_max=10,
    )

    random_seed = IntProperty(
        name="Random seed",
        description="Root random seed value used to generate randomized stuff in this show file",
        default=0,
        min=1,
        soft_min=1,
        soft_max=RANDOM_SEED_MAX,
    )

    show_orientation = FloatProperty(
        name="Show orientation",
        description="Proposed orientation of the X+ axis of the show coordinate system relative to North (towards East)",
        default=0.0,
        subtype="ANGLE",
        precision=3,
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
        update=show_type_updated,
    )

    use_bloom_effect = BoolProperty(
        name="Use bloom effect",
        description="Specifies whether the bloom effect should automatically be enabled on the 3D View when the show is loaded",
        default=True,
        update=use_bloom_effect_updated,
    )

    use_show_origin_and_orientation = BoolProperty(
        name="Use show origin and orientation",
        description="Specifies whether to have a proposed show origin and orientation, e.g., used in .skyc export",
        default=False,
        update=use_bloom_effect_updated,
    )

    time_markers = StringProperty(
        name="Time markers",
        description=(
            "Names of the timeline markers that were created by the plugin and "
            "that may be removed when the 'Update Time Markers' operation "
            "is triggered"
        ),
        default="",
        options={"HIDDEN"},
    )

    emission_strength = FloatProperty(
        name="Emission",
        description="Specifies the light emission strength of the drone meshes",
        default=float(DEFAULT_EMISSION_STRENGTH),
        update=emission_strength_updated,
        min=0,
        soft_min=0,
        soft_max=5,
        precision=2,
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
