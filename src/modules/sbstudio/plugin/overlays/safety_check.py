import bgl
import bpy
import gpu

from gpu_extras.batch import batch_for_shader

from .base import Overlay

__all__ = ("SafetyCheckOverlay",)


class SafetyCheckOverlay(Overlay):
    """Overlay that marks a closest pair of drones in the 3D view."""

    def __init__(self):
        super().__init__()

        self._nearest_neighbor_coords = None
        self._nearest_neighbor_batch = None

    @property
    def nearest_neighbor_coords(self):
        return self._nearest_neighbor_coords

    @nearest_neighbor_coords.setter
    def nearest_neighbor_coords(self, value):
        if value is not None:
            first, second = value
            value = tuple(float(x) for x in first), tuple(float(x) for x in second)

        self._nearest_neighbor_coords = value
        self._nearest_neighbor_batch = None

    def prepare(self) -> None:
        self._shader = gpu.shader.from_builtin("3D_UNIFORM_COLOR")

    def draw(self) -> None:
        bgl.glEnable(bgl.GL_BLEND)

        if self._nearest_neighbor_coords is not None:
            if self._nearest_neighbor_batch is None:
                self._nearest_neighbor_batch = [
                    batch_for_shader(
                        self._shader,
                        "LINES",
                        {"pos": self._nearest_neighbor_coords},
                    ),
                    batch_for_shader(
                        self._shader,
                        "POINTS",
                        {"pos": self._nearest_neighbor_coords},
                    ),
                ]

            safety_check = bpy.context.scene.skybrush.safety_check
            threshold = safety_check.proximity_warning_threshold
            if threshold > 0 and safety_check.min_distance < threshold:
                color = (1, 0, 0, 1)
            else:
                color = (0, 1, 0, 1)

            self._shader.bind()
            self._shader.uniform_float("color", color)
            bgl.glLineWidth(5)
            bgl.glPointSize(20)
            for batch in self._nearest_neighbor_batch:
                batch.draw(self._shader)

    def dispose(self) -> None:
        self._nearest_neighbor_batch = None
        self._shader = None
