from bpy.props import EnumProperty

from sbstudio.plugin.model.storyboard import get_storyboard
from sbstudio.utils import consecutive_pairs

__all__ = (
    "StoryboardEntryOrTransitionProperty",
    "StoryboardEntryProperty",
)


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


def _get_storyboard_entries_and_transitions(self, context):
    # Note that this list will be updated dynamically,
    # so the user of this class needs to take care of
    # restoring the last selected entry if the items
    # list changes.
    storyboard = get_storyboard(context=context)
    retval = [("NONE", "-", "", 0)]
    i = 1
    for prev, next in consecutive_pairs(storyboard.entries):
        retval.append((prev.id, prev.name, "", i))
        i += 1
        retval.append((f"{prev.id}..{next.id}", f"{prev.name} -> {next.name}", "", i))
        i += 1
    if storyboard.last_entry is not None:
        retval.append((storyboard.last_entry.id, storyboard.last_entry.name, "", i))

    return retval


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


def StoryboardEntryOrTransitionProperty(**kwds):
    """Factory function disguised as a class; creates a Blender property that
    is suitable for storing a pointer to a storyboard entry or a transition
    between storyboard entries.
    """
    props = {
        "name": "Storyboard Entry/Transition",
        "items": _get_storyboard_entries_and_transitions,
    }
    props.update(kwds)
    return EnumProperty(**props)
