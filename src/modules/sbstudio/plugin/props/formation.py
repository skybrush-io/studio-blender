from bpy.props import PointerProperty
from bpy.types import Collection

from sbstudio.plugin.model.formation import is_formation

__all__ = ("FormationProperty",)


def _is_formation(self, object):
    return is_formation(object)


def FormationProperty(**kwds):
    """Factory function disguised as a class; creates a Blender property that
    is suitable for storing a pointer to a formation.
    """
    props = {
        "name": "Formation",
        "type": Collection,
        "poll": _is_formation,
    }
    props.update(kwds)
    return PointerProperty(**props)
