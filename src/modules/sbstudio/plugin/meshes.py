"""Functions related to the handling of meshes used in the Blender
visualizations.
"""

import bmesh
import bpy

from contextlib import contextmanager
from mathutils import Matrix
from typing import Optional

from sbstudio.model.types import Coordinate3D

from .objects import create_object

__all__ = (
    "create_cube",
    "create_icosphere",
    "edit_mesh",
    "subdivide_edges",
)


def _current_object_renamed_to(name):
    result = bpy.context.object
    if name is not None:
        result.name = name
    return result


def create_cube(
    center: Coordinate3D = (0, 0, 0),
    size: float = 1,
    *,
    name: Optional[str] = None,
):
    """Creates a Blender mesh object with the shape of a cube.

    Parameters:
        center: the center of the cube
        size: the size of the cube. You may also pass a tuple of length 3
            to create a box with different width, height and depth.
        name: the name of the mesh object; `None` to use the default name that
            Blender assigns to the object

    Returns:
        object: the created mesh object
    """
    if isinstance(size, (int, float)):
        size = (size, size, size)

    bpy.ops.mesh.primitive_cube_add(location=center)
    bpy.context.object.scale = size

    return _current_object_renamed_to(name)


def create_icosphere(
    center: Coordinate3D = (0, 0, 0), radius: float = 1, *, name: Optional[str] = None
):
    """Creates a Blender icosphere mesh object.

    Parameters:
        center: the center of the icosphere
        radius: the radius of the icosphere
        name: the name of the mesh object; `None` to use the default name that
            Blender assigns to the object

    Returns:
        object: the created mesh object
    """
    with use_b_mesh() as bm:
        bmesh.ops.create_icosphere(
            bm, subdivisions=2, radius=radius, matrix=Matrix(), calc_uvs=True
        )
        obj = create_object_from_bmesh(bm, name=name or "Icosphere")

    obj.location = center
    return obj


def create_object_from_bmesh(bm, *, name: Optional[str] = None):
    """Creates a new Blender object from a B-mesh representation.

    Parameters:
        bm: the B-mesh to use
        name: the name of the newly created object
        free: whether to free the B-mesh after the mesh representation was
            created

    Returns:
        the newly created object
    """
    mesh = bpy.data.meshes.new("Mesh")
    bm.to_mesh(mesh)

    obj = create_object(name or "Object", mesh)
    mesh.name = f"{obj.name} Mesh"

    return obj


def create_sphere(
    center: Coordinate3D = (0, 0, 0),
    radius: float = 1,
    *,
    name: Optional[str] = None,
):
    """Creates a Blender mesh object with the shape of a sphere.

    Parameters:
        center: the center of the sphere
        radius: the radius of the sphere
        name: the name of the mesh object; `None` to use the default name that
            Blender assigns to the object

    Returns:
        object: the created mesh object
    """
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=center)
    return _current_object_renamed_to(name)


@contextmanager
def edit_mesh(obj):
    """Establishes a context in which the mesh of the given Blender object
    is converted into a B-mesh representation for easier editing. The B-mesh
    representation will be converted back to the original mesh upon exiting
    the context normally. When an exception is raised in the context, the
    editing operations are discarded.

    Parameters:
        obj (object): the Blender object whose mesh should be edited

    Yields:
        object: the B-mesh representation of the mesh
    """
    if isinstance(obj, bmesh.types.BMesh):
        yield obj
    elif isinstance(obj, bpy.types.Mesh):
        with use_b_mesh() as result:
            result.from_mesh(obj)
            yield result
            result.to_mesh(obj)
    else:
        with use_b_mesh() as result:
            result.from_mesh(obj.data)
            yield result
            result.to_mesh(obj.data)


@contextmanager
def use_b_mesh():
    """Context manager that creates a new B-mesh object when entering the
    context and frees the B-mesh object when exiting the context.
    """
    result = bmesh.new()
    try:
        yield result
    finally:
        result.free()


def subdivide_edges(obj, cuts=1):
    """Subdivides the edges of the mesh of the given object.

    Parameters:
        obj (object): the Blender object whose mesh is to be subdivided
        cuts (int): the number of cuts to apply per edge
    """
    if cuts <= 0:
        return

    with edit_mesh(obj) as mesh:
        bmesh.ops.subdivide_edges(mesh, edges=mesh.edges, use_grid_fill=True, cuts=cuts)
