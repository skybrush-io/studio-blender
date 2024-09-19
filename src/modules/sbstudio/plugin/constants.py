from __future__ import annotations

import bpy

from bpy.types import Collection
from functools import partial
from typing import (
    Callable,
    ClassVar,
    Literal,
    Optional,
    TypeVar,
    TYPE_CHECKING,
    overload,
)

from .materials import create_glowing_material
from .meshes import create_icosphere, create_cone
from .utils import (
    ensure_object_exists_in_collection,
    get_object_in_collection,
)

if TYPE_CHECKING:
    from bpy.types import bpy_prop_collection, ID
    from .model import DroneShowAddonProperties

__all__ = ("Collections", "Templates")


DEFAULT_EMISSION_STRENGTH = 1
"""Default strength of the emission node of the LED material"""

DEFAULT_STORYBOARD_ENTRY_DURATION = 20
"""Default duration of newly created storyboard entries, in seconds"""

DEFAULT_STORYBOARD_TRANSITION_DURATION = 20
"""Default duration of transitions to leave between storyboard entries, in seconds"""

DEFAULT_LIGHT_EFFECT_DURATION = 10
"""Default duration of newly created light effects, in seconds"""

DRONE_RADIUS = 0.5
"""Drone radius"""

RANDOM_SEED_MAX = 0x7FFFFFFF
"""Maximum allowed value of the random seed. Note that Blender does not support
integer properties larger than a 32-bit signed int, hence the limit.
"""

T = TypeVar("T", covariant=True, bound="ID")


class Collections:
    DRONES: ClassVar[str] = "Drones"
    """Name of the collection that holds the drones"""

    FORMATIONS: ClassVar[str] = "Formations"
    """Name of the collection that holds the formations"""

    TEMPLATES: ClassVar[str] = "Templates"
    """Name of the collection that holds the object templates"""

    @classmethod
    @overload
    def find_drones(cls, *, create: Literal[True] = True) -> Collection: ...

    @classmethod
    @overload
    def find_drones(cls, *, create: bool) -> Optional[Collection]: ...

    @classmethod
    def find_drones(cls, *, create: bool = True):
        # Return the collection specified in the settings if the user specified
        # one; otherwise fall back to finding the collection by name.
        if bpy.context.scene:
            skybrush: Optional[DroneShowAddonProperties] = getattr(
                bpy.context.scene, "skybrush", None
            )
            collection = skybrush.settings.drone_collection if skybrush else None
            if collection:
                return collection

        return cls._find(
            cls.DRONES, create=create, on_created=cls._on_drone_collection_created
        )

    @classmethod
    @overload
    def find_formations(cls, *, create: Literal[True] = True) -> Collection: ...

    @classmethod
    @overload
    def find_formations(cls, *, create: bool) -> Optional[Collection]: ...

    @classmethod
    def find_formations(cls, *, create: bool = True):
        return cls._find(cls.FORMATIONS, create=create)

    @classmethod
    @overload
    def find_templates(cls, *, create: Literal[True] = True) -> Collection: ...

    @classmethod
    @overload
    def find_templates(cls, *, create: bool) -> Optional[Collection]: ...

    @classmethod
    def find_templates(cls, *, create: bool = True):
        return cls._find(cls.TEMPLATES, create=create)

    @classmethod
    @overload
    def _find(
        cls,
        key: str,
        *,
        create: Literal[True] = True,
        on_created: Optional[Callable[[Collection], None]] = None,
    ) -> Collection: ...

    @classmethod
    @overload
    def _find(
        cls,
        key: str,
        *,
        create: bool,
        on_created: Optional[Callable[[Collection], None]] = None,
    ) -> Optional[Collection]: ...

    @classmethod
    def _find(
        cls,
        key: str,
        *,
        create: bool = True,
        on_created: Optional[Callable[[Collection], None]] = None,
    ):
        """Returns the Blender collection with the given name, and optionally
        creates it if it does not exist yet.
        """
        return cls._find_in(
            bpy.data.collections, key, create=create, on_created=on_created
        )

    @classmethod
    def _find_in(
        cls,
        coll: bpy_prop_collection[T],
        key: str,
        *,
        create: bool = True,
        on_created: Optional[Callable[[T], None]] = None,
    ) -> Optional[T]:
        """Returns an object from a Blender collection given its name, and
        optionally creates it if it does not exist yet.
        """
        if create:
            result, is_new = ensure_object_exists_in_collection(coll, key)
            if is_new and on_created:
                on_created(result)
            return result
        else:
            return get_object_in_collection(coll, key, default=None)

    @classmethod
    def _on_drone_collection_created(cls, obj) -> None:
        bpy.context.scene.skybrush.settings.drone_collection = obj


class Formations:
    TAKEOFF_GRID: ClassVar[str] = "Takeoff grid"
    """Name of the takeoff grid formation"""

    TAKEOFF: ClassVar[str] = "Takeoff"
    """Name of the takeoff formation (hovering above the takeoff grid)"""

    @classmethod
    @overload
    def find_takeoff_grid(cls, *, create: Literal[True] = True) -> Collection: ...

    @classmethod
    @overload
    def find_takeoff_grid(cls, *, create: bool) -> Optional[Collection]: ...

    @classmethod
    def find_takeoff_grid(cls, *, create: bool = True) -> Optional[Collection]:
        """Returns the Blender collection that represents the takeoff grid or
        ``None`` if no takeoff grid was created yet.
        """
        formations = Collections.find_formations(create=create)
        if formations:
            return Collections._find_in(
                formations.children, cls.TAKEOFF_GRID, create=create
            )
        else:
            return None


class Templates:
    DRONE: ClassVar[str] = "Drone template"
    """Name of the drone template object"""

    @classmethod
    def find_drone(cls, *, create: bool = True, template: str = "SPHERE"):
        """Returns the Blender object that serves as a template for newly
        created drones.

        Args:
            template: the drone template to use.
                Possible values: SPHERE, CONE, SELECTED
            create: whether to create the template if it does not exist yet

        """
        templates = Collections.find_templates()
        coll = templates.objects
        if create:
            drone, _ = ensure_object_exists_in_collection(
                coll,
                cls.DRONE,
                factory=partial(cls._create_drone_template, template=template),
            )
            return drone
        else:
            return get_object_in_collection(coll, cls.DRONE)

    @staticmethod
    def _create_drone_template(template: str = "SPHERE"):
        if template == "SPHERE":
            object = create_icosphere(radius=DRONE_RADIUS)
        elif template == "CONE":
            object = create_cone(radius=DRONE_RADIUS)
        elif template == "SELECTED":
            objects = bpy.context.selected_objects
            if not objects:
                object = create_icosphere(radius=DRONE_RADIUS)
            else:
                object = objects[0]
        else:
            raise ValueError(f"Unknown drone template name: {template!r}")

        # We remove the object from all collections it is in.
        for collection in bpy.data.collections:
            if object.name in collection.objects:
                collection.objects.unlink(object)
        if object.name in bpy.context.scene.collection.objects:
            bpy.context.scene.collection.objects.unlink(object)

        # Hide the object from the viewport and the render
        object.hide_viewport = True
        object.hide_select = True
        object.hide_render = True

        # Add a shiny light emission to the object
        material = create_glowing_material(
            "Drone template material", strength=DEFAULT_EMISSION_STRENGTH
        )
        object.active_material = material

        # Make sure that the object is not selected
        object.select_set(False)

        return object
