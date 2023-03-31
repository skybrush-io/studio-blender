from sbstudio.plugin.constants import Collections

__all__ = ("get_drone_count",)


def get_drone_count() -> int:
    """Returns the number of drones in the current scene."""
    drones = Collections.find_drones(create=False)
    return 0 if drones is None else len(drones.objects)
