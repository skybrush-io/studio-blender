from bpy.types import Context

from sbstudio.model.cameras import Camera


__all__ = ("get_cameras_from_context",)


def get_cameras_from_context(context: Context) -> list[Camera]:
    """Get cameras from the Skybrush or native Blender context.

    Args:
        context: the main Blender context

    Returns:
        list of Blender cameras for later use by Skybrush

    """
    cameras = [obj for obj in context.scene.objects if obj.type == "CAMERA"]

    retval = []
    for camera in cameras:
        rotation_mode = camera.rotation_mode
        camera.rotation_mode = "QUATERNION"
        retval.append(
            Camera(
                name=camera.name,
                position=tuple(camera.location),
                orientation=tuple(camera.rotation_quaternion),
            )
        )
        camera.rotation_mode = rotation_mode

    return retval
