from bpy.props import EnumProperty

from sbstudio.plugin.model.storyboard import get_storyboard

__all__ = ("StoryboardEntryProperty",)


def _get_storyboard_entries(self, context):
    # Note that this list will be updated dynamically,
    # so the user of this class needs to take care of
    # restoring the last selected entry if the items
    # list changes.
    storyboard = get_storyboard(context=context)
    return [("NONE", "-", "", 0)] + [
        (entry.id, entry.name, "", i)
        for i, entry in enumerate(storyboard.entries, start=1)
    ]


def StoryboardEntryProperty(**kwds):
    """Factory function disguised as a class; creates a Blender property that
    is suitable for storing a pointer to a storyboard entry.
    """
    props = {
        "name": "Storyboard Entry",
        "items": _get_storyboard_entries,
    }
    props.update(kwds)
    return EnumProperty(**props)
