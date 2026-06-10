from bpy.types import Context, UILayout

from sbstudio.plugin.migrations import get_migration_details
from sbstudio.plugin.model.formation import count_markers_in_formation
from sbstudio.plugin.model.led_control import (
    get_expected_3d_viewport_shader_configuration_from_context,
)
from sbstudio.plugin.stats import get_drone_count
from sbstudio.plugin.views import find_current_3d_view

__all__ = (
    "draw_bad_shader_color_source_warning",
    "draw_experimental_feature_warning",
    "draw_formation_size_warning",
    "draw_version_warning",
    "get_bad_shader_color_source_warning",
)


def _draw_warning(layout, text: str) -> None:
    row = layout.box()
    row.alert = False
    row.label(text=text, icon="ERROR")


def get_bad_shader_color_source_warning(context: Context) -> str | None:
    """Returns a warning label if the shader configuration is bad,
    `None` otherwise."""
    space = find_current_3d_view(context)
    if space is None:
        return None

    shading = space.shading

    expected_wireframe_color_type, expected_color_type = (
        get_expected_3d_viewport_shader_configuration_from_context(context)
    )

    label = (
        f"Set shader Wireframe Color to {expected_wireframe_color_type!r}"
        if (
            shading.type == "WIREFRAME"
            and expected_wireframe_color_type is not None
            and shading.wireframe_color_type != expected_wireframe_color_type
        )
        else f"Set shader Object Color to {expected_color_type!r}"
        if (
            shading.type == "SOLID"
            and expected_color_type is not None
            and shading.color_type != expected_color_type
        )
        else None
    )

    return label


def draw_bad_shader_color_source_warning(context: Context, layout: UILayout) -> None:
    """Draw a bad shader color source warning to a layout, if needed."""
    label = get_bad_shader_color_source_warning(context)
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


def draw_experimental_feature_warning(
    layout: UILayout, *, message: str = "This feature is experimental"
) -> None:
    """Draw an experimental feature warning to a layout."""
    _draw_warning(layout, message)


def draw_version_warning(context: Context, layout: UILayout) -> None:
    """Draw a version warning to a layout, if needed."""
    migration_needed, current_version, max_version = get_migration_details(context)
    if migration_needed:
        _draw_warning(
            layout,
            text=f"File format too old (version {current_version} < {max_version})",
        )
