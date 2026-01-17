from collections.abc import Iterator

from bpy.props import EnumProperty

from sbstudio.plugin.model.light_effects import LightEffect, LightEffectCollection

__all__ = ("LightEffectSelectionProperty",)


def LightEffectSelectionProperty(add_selected: bool = True, **kwds):
    """Factory function disguised as a class; creates a Blender property that
    is suitable for selecting one or more light effects.
    """
    items = [
        ("ALL", "All", "Select all light effects"),
        ("ENABLED", "Enabled", "Select all enabled light effects"),
    ]
    if add_selected:
        items.append(
            ("SELECTED", "Selected", "Select only the currently active light effect")
        )

    props = {
        "name": "Light effects",
        "description": "Choose a filter type to use for this operation",
        "items": items,
        "default": "ALL",
    }
    props.update(kwds)

    return EnumProperty(**props)


def iterate_light_effects_from_selection(
    light_effects: LightEffectCollection,
    selection: str,
) -> Iterator[LightEffect]:
    """Returns an iterator of light effects based on the given selection criterium."""
    if not light_effects.entries:
        return
    if selection == "SELECTED":
        if light_effects.active_entry is None:
            return
        yield light_effects.active_entry
    elif selection == "ALL":
        yield from light_effects.entries
    elif selection == "ENABLED":
        yield from (effect for effect in light_effects.entries if effect.enabled)
    else:
        raise RuntimeError(f"Unknown light effect selector: {selection!r}")
