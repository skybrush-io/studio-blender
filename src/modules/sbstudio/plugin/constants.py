import bpy

from typing import Callable, Optional

from .materials import create_glowing_material
from .meshes import create_icosphere
from .utils import (
    ensure_object_exists_in_collection,
    get_object_in_collection,
)

__all__ = ("Collections", "Templates")


#: Default duration of newly created storyboard entries, in seconds
DEFAULT_STORYBOARD_ENTRY_DURATION = 20

#: Default duration of transitions to leave between storyboard entries,
#: in seconds
DEFAULT_STORYBOARD_TRANSITION_DURATION = 20

#: Default duraition of newly created light effects, in seconds
DEFAULT_LIGHT_EFFECT_DURATION = 10

#: Drone radius
DRONE_RADIUS = 0.5


class Collections:
    #: Name of the collection that holds the drones
    DRONES = "Drones"

    #: Name of the collection that holds the formations
    FORMATIONS = "Formations"

    #: Name of the collection that holds the object templates
    TEMPLATES = "Templates"

    @classmethod
    def find_drones(cls, *, create: bool = True):
        # Return the collection specified in the settings if the user specified
        # one; otherwise fall back to finding the collection by name.
        if bpy.context.scene:
            skybrush = getattr(bpy.context.scene, "skybrush", None)
            collection = skybrush.settings.drone_collection if skybrush else None
            if collection:
                return collection

        return cls._find(
            cls.DRONES, create=create, on_created=cls._on_drone_collection_created
        )

    @classmethod
    def find_formations(cls, *, create: bool = True):
        return cls._find(cls.FORMATIONS, create=create)

    @classmethod
    def find_templates(cls, *, create: bool = True):
        return cls._find(cls.TEMPLATES, create=create)

    @classmethod
    def _find(
        cls,
        key: str,
        *,
        create: bool = True,
        on_created: Optional[Callable[[bpy.types.Object], None]] = None
    ):
        """Returns the Blender collection that holds the drones, and optionally
        creates it if it does not exist yet.
        """
        coll = bpy.data.collections
        if create:
            result = ensure_object_exists_in_collection(coll, key)
            if on_created:
                on_created(result)
            return result
        else:
            return get_object_in_collection(coll, key, default=None)

    @classmethod
    def _on_drone_collection_created(cls, obj) -> None:
        bpy.context.scene.skybrush.settings.drone_collection = obj


class Templates:
    #: Name of the drone template object
    DRONE = "Drone template"

    @classmethod
    def find_drone(cls, *, create: bool = True):
        """Returns the Blender object that serves as a template for newly
        created drones, and optionally creates it if it does not exist yet.
        """
        templates = Collections.find_templates()
        coll = templates.objects
        if create:
            return ensure_object_exists_in_collection(
                coll, cls.DRONE, factory=cls._create_drone_template
            )
        else:
            return get_object_in_collection(coll, cls.DRONE)

    @staticmethod
    def _create_drone_template():
        object = create_icosphere(radius=DRONE_RADIUS)

        # The icosphere is created in the current scene collection of the Blender
        # context, but we don't need it there so let's remove it.
        bpy.context.scene.collection.objects.unlink(object)

        # Hide the object from the viewport and the render
        object.hide_viewport = True
        object.hide_select = True
        object.hide_render = True

        # Add a shiny light emission to the object
        material = create_glowing_material("Drone template material")
        object.active_material = material

        # Make sure that the object is not selected
        object.select_set(False)

        return object
