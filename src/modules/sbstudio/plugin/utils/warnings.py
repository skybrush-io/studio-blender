from typing import cast

from bpy.types import Context, SpaceView3D, UILayout

from sbstudio.plugin.migrations import get_migration_details
from sbstudio.plugin.model.formation import count_markers_in_formation
from sbstudio.plugin.stats import get_drone_count

__all__ = (
    "draw_bad_shader_color_source_warning",
    "draw_formation_size_warning",
    "draw_version_warning",
)


def _draw_warning(layout, text: str) -> None:
    row = layout.box()
    row.alert = False
    row.label(text=text, icon="ERROR")


def draw_bad_shader_color_source_warning(context: Context, layout: UILayout) -> None:
    """Draw a bad shader color source warning to a layout, if needed."""
    space = context.space_data
    if not space or space.type != "VIEW_3D":
        return

    space = cast(SpaceView3D, space)
    shading = space.shading

    label = (
        "Set shader Wireframe Color to 'OBJECT'"
        if (shading.type == "WIREFRAME" and shading.wireframe_color_type != "OBJECT")
        else "Set shader Object Color to 'OBJECT'"
        if (shading.type == "SOLID" and shading.color_type != "OBJECT")
        else None
    )
    if label:
        _draw_warning(layout, text=label)


def draw_formation_size_warning(context: Context, layout: UILayout) -> None:
    """Draw a formation size warning to a layout, if needed."""
    formations = context.scene.skybrush.formations
    if not formations:
        return

    selected_formation = formations.selected
    if not selected_formation:
        return

    num_drones = get_drone_count()
    num_markers = count_markers_in_formation(selected_formation)

    # If the number of markers in the formation is different from the
    # number of drones, show a warning as we won't know what to do with
    # the extra or missing drones
    if num_markers != num_drones:
        _draw_warning(
            layout,
            text=f"Formation size: {num_markers} "
            f"{'<' if num_markers < num_drones else '>'} "
            f"{num_drones}",
        )


def draw_version_warning(context: Context, layout: UILayout) -> None:
    """Draw a version warning to a layout, if needed."""
    migration_needed, current_version, max_version = get_migration_details(context)
    if migration_needed:
        _draw_warning(
            layout,
            text=f"File format too old (version {current_version} < {max_version})",
        )
