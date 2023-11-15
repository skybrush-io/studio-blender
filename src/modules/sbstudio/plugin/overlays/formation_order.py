import bpy
import gpu

from gpu_extras.batch import batch_for_shader
from numpy import linspace

from sbstudio.plugin.model.formation import (
    get_world_coordinates_of_markers_from_formation,
)

from .base import ShaderOverlay

try:
    import gpu.state

    has_gpu_state_module = True
except ImportError:
    import bgl

    has_gpu_state_module = False

__all__ = ("FormationOrderOverlay",)


class FormationOrderOverlay(ShaderOverlay):
    """Overlay that shows the order of markers in the currently selected formation
    in the 3D view.
    """

    shader_type = "SMOOTH_COLOR"

    def draw_3d(self) -> None:
        if has_gpu_state_module:
            gpu.state.blend_set("ALPHA")
        else:
            bgl.glEnable(bgl.GL_BLEND)

        # TODO(ntamas): cache if possible. We would need to listen for events
        # that are triggered when the selected formation changes or when any
        # mesh within the selected formation changes
        batch = self._create_shader_batch()

        if batch:
            self._shader.bind()
            if has_gpu_state_module:
                gpu.state.line_width_set(3)
            else:
                bgl.glLineWidth(3)
            batch.draw(self._shader)

    def _create_shader_batch(self):
        try:
            formation = bpy.context.scene.skybrush.formations.selected
        except Exception:
            formation = None

        if formation:
            coords = get_world_coordinates_of_markers_from_formation(formation).tolist()

            # Use a gradient from green to red, green = start, red = stop
            colors = [(frac, 1 - frac, 0, 1) for frac in linspace(0, 1, len(coords))]
            return batch_for_shader(
                self._shader, "LINE_STRIP", {"pos": coords, "color": colors}
            )
