from bpy.types import Context

from sbstudio.plugin.constants import LATEST_SKYBRUSH_PLUGIN_VERSION
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


def draw_bad_shader_color_source_warning(context: Context, layout) -> None:
    """Draw a bad shader color source warning to a layout, if needed."""
    shading = context.space_data.shading
    label = (
        "Set shader Wireframe Color to 'OBJECT'"
        if (shading.type == "WIREFRAME" and shading.wireframe_color_type != "OBJECT")
        else "Set shader Object Color to 'OBJECT'"
        if (shading.type == "SOLID" and shading.color_type != "OBJECT")
        else None
    )
    if label:
        _draw_warning(layout, text=label)


def draw_formation_size_warning(context: Context, layout) -> None:
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


def draw_version_warning(context: Context, layout) -> None:
    """Draw a version warning to a layout, if needed."""
    skybrush = context.scene.skybrush
    if skybrush.version < LATEST_SKYBRUSH_PLUGIN_VERSION:
        _draw_warning(
            layout,
            text=f"File format is old (version {skybrush.version} < {LATEST_SKYBRUSH_PLUGIN_VERSION})",
        )
