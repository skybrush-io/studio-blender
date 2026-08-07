from pathlib import Path
from tempfile import gettempdir

import bpy
from bpy.types import Context

from sbstudio.model.terrain import Terrain
from sbstudio.plugin.constants import Collections

__all__ = ("get_terrain_from_context",)


def get_terrain_from_context(context: Context) -> Terrain | None:
    """Get terrain from the Skybrush or native Blender context

    Args:
        context: the main Blender context

    Returns:
        terrain object for later use by Skybrush, or `None` if
        no terrain could be gathered.

    """

    terrain_collection = Collections.find_terrain(create=False)
    if terrain_collection is None:
        return None

    glb_path = (
        Path(gettempdir())
        / "skybrush-studio"
        / Path(bpy.data.filepath).stem
        / "terrain.glb"
    )
    glb_path.parent.mkdir(parents=True, exist_ok=True)
    glb_file = glb_path.as_posix()

    # Note that calling .glb export might take a while if there are many objects
    # in the Terrain collection
    bpy.ops.export_scene.gltf(filepath=glb_file, collection=terrain_collection.name)

    return Terrain(file_path=glb_file)
