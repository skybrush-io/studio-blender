from pathlib import Path
from tempfile import TemporaryDirectory

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

    Raises:
        RuntimeError on error
    """

    terrain_collection = Collections.find_terrain(create=False)
    if terrain_collection is None or not terrain_collection.all_objects:
        return None

    with TemporaryDirectory() as tmp_dir:
        glb_path = Path(tmp_dir) / "terrain.glb"

        # Note that calling .glb export might take a while if there are
        # many objects in the Terrain collection
        result = bpy.ops.export_scene.gltf(
            filepath=glb_path.as_posix(),
            collection=terrain_collection.name,
            export_format="GLB",
        )

        if "FINISHED" not in result:
            raise RuntimeError("Could not finish terrain export")

        return Terrain(data=glb_path.read_bytes())
