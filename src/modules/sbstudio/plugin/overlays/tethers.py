import blf
import bpy
import gpu

from gpu_extras.batch import batch_for_shader
from typing import Any, Optional, List, Sequence, Tuple

from sbstudio.model.types import Coordinate3D

from .base import ShaderOverlay

try:
    import gpu.state

    has_gpu_state_module = True
except ImportError:
    import bgl

    has_gpu_state_module = False

__all__ = ("TetherOverlay",)

#: Type specification for tethers. Each tether is a tuple of start and end
# coordinates that are interconnected with a straight line segment
TetherList = List[Tuple[Coordinate3D, Coordinate3D]]


class TetherOverlay(ShaderOverlay):
    """Overlay that connects drones with their home position so that the become
    tethered in the visualization.
    """

    _tethers: Optional[TetherList] = None

    _shader_batches: Any

    def __init__(self):
        super().__init__()

        self._shader_batches = None

    @property
    def tethers(self) -> Optional[TetherList]:
        return self._tethers

    @tethers.setter
    def tethers(self, value):
        if value is not None:
            self._tethers = []
            for tether_points in value:
                tether_points = tuple(
                    tuple(float(coord) for coord in point) for point in tether_points
                )
                self._tethers.append(tether_points)

        else:
            self._tethers = None

        self._shader_batches = None

    def draw_3d(self) -> None:
        if has_gpu_state_module:
            gpu.state.blend_set("ALPHA")
        else:
            bgl.glEnable(bgl.GL_BLEND)

        if self._tethers is not None:
            if self._shader_batches is None:
                self._shader_batches = self._create_shader_batches()

            if self._shader_batches:
                self._shader.bind()
                self._shader.uniform_float("color", (0.5, 0.5, 0.5, 1))
                if has_gpu_state_module:
                    gpu.state.line_width_set(3)
                else:
                    bgl.glLineWidth(3)
                for batch in self._shader_batches:
                    if has_gpu_state_module:
                        # hints: https://docs.blender.org/api/current/gpu.html
                        gpu.state.depth_test_set("LESS_EQUAL")
                        gpu.state.depth_mask_set(True)
                    else:
                        # TODO: what is the equivalent of
                        # gpu.state.depth_test_set("LESS_EQUAL")
                        bgl.glDepthMask(bgl.GL_TRUE)
                    batch.draw(self._shader)
                    if has_gpu_state_module:
                        gpu.state.depth_mask_set(False)
                    else:
                        bgl.glDepthMask(bgl.GL_FALSE)

    def dispose(self) -> None:
        super().dispose()
        self._shader_batches = None

    def _create_shader_batches(self):
        batches, points, lines = [], [], []

        for tether_points in self._tethers or ():
            points.extend(tether_points)

            if tether_points:
                if len(tether_points) > 2:
                    prev = points[-1]
                    for curr in tether_points:
                        lines.extend((prev, curr))
                        prev = curr
                elif len(tether_points) == 2:
                    lines.extend(tether_points)

        # Construct the shader batch to draw the lines on the UI
        batches.extend(
            [
                batch_for_shader(self._shader, "LINES", {"pos": lines}),
            ]
        )

        return batches
