import bgl
import gpu

from gpu_extras.batch import batch_for_shader
from typing import List, Sequence

from sbstudio.model.types import Coordinate3D

from .base import Overlay

__all__ = ("SafetyCheckOverlay",)

#: Type specification for markers on the overlay. Each marker is a sequence of
#: coordinates that are interconnected with lines.
MarkerList = List[Sequence[Coordinate3D]]


class SafetyCheckOverlay(Overlay):
    """Overlay that marks the closest pair of drones and all drones above the
    altitude threshold in the 3D view.
    """

    def __init__(self):
        super().__init__()

        self._markers = None
        self._shader_batches = None

    @property
    def markers(self):
        return self._markers

    @markers.setter
    def markers(self, value):
        if value is not None:
            self._markers = []
            for marker_points in value:
                marker_points = tuple(
                    tuple(float(coord) for coord in point) for point in marker_points
                )
                self._markers.append(marker_points)

        else:
            self._markers = None

        self._shader_batches = None

    def prepare(self) -> None:
        self._shader = gpu.shader.from_builtin("3D_UNIFORM_COLOR")

    def draw(self) -> None:
        bgl.glEnable(bgl.GL_BLEND)

        if self._markers is not None:
            if self._shader_batches is None:
                self._shader_batches = self._create_shader_batches()

            if self._shader_batches:
                self._shader.bind()
                self._shader.uniform_float("color", (1, 0, 0, 1))
                bgl.glLineWidth(5)
                bgl.glPointSize(20)
                for batch in self._shader_batches:
                    batch.draw(self._shader)

    def dispose(self) -> None:
        self._shader = None
        self._shader_batches = None

    def _create_shader_batches(self) -> None:
        batches, points, lines = [], [], []

        for marker_points in self._markers:
            points.extend(marker_points)

            if marker_points:
                if len(marker_points) > 2:
                    prev = points[-1]
                    for curr in marker_points:
                        lines.extend((prev, curr))
                        prev = curr
                elif len(marker_points) == 2:
                    lines.extend(marker_points)

        # Construct the shader batch to draw the lines on the UI
        batches.extend(
            [
                batch_for_shader(self._shader, "LINES", {"pos": lines}),
                batch_for_shader(self._shader, "POINTS", {"pos": points}),
            ]
        )

        return batches
