"""Background task that is invoked after every frame change and draws
markers on drones when their pyro effect is active.
"""

from __future__ import annotations

import bpy

from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING

from sbstudio.plugin.constants import Collections
from sbstudio.plugin.overlays.pyro import (
    DEFAULT_PYRO_OVERLAY_MARKER_COLOR,
    PyroOverlayInfo,
    PyroOverlayMarker,
)
from sbstudio.plugin.utils.evaluator import get_position_of_object
from sbstudio.plugin.utils.pyro_markers import get_pyro_markers_of_object

# from sbstudio.plugin.utils import debounced

from .base import Task

if TYPE_CHECKING:
    from bpy.types import Scene

_suspension_counter = 0
"""Suspension counter. Pyro marker overlay is suspended if this counter is positive."""


# @debounced(delay=0.1)
def run_update_pyro_overlay_markers(scene: Scene, depsgraph) -> None:
    global _suspension_counter
    if _suspension_counter > 0:
        return

    pyro_control = scene.skybrush.pyro_control

    if pyro_control.visualization in ["MARKERS", "INFO"]:
        drones = Collections.find_drones(create=False)
    else:
        drones = None

    if not drones:
        pyro_control.clear_pyro_overlay_markers()
        return

    # Get position of drones from the current frame that have
    # active pyro effect at the moment
    frame = scene.frame_current
    fps = scene.render.fps
    overlay_markers: list[PyroOverlayMarker] = []
    overlay_info_blocks: list[PyroOverlayInfo] = []
    for drone in drones.objects:
        markers = get_pyro_markers_of_object(drone)
        info_lines = []
        position = None
        for channel, marker in markers.markers.items():
            if pyro_control.visualization == "INFO" or marker.is_active_at_frame(
                frame, fps
            ):
                if position is None:
                    position = get_position_of_object(drone)
                # TODO: change color with pyro channel
                color = DEFAULT_PYRO_OVERLAY_MARKER_COLOR
                overlay_markers.append((position, color))
                info_lines.append(f"C{channel} F{marker.frame}: {marker.payload.name}")
        if info_lines:
            assert position is not None
            overlay_info_blocks.append((position, info_lines))

    pyro_control.update_pyro_overlay_markers(overlay_markers)
    pyro_control.update_pyro_overlay_info_blocks(overlay_info_blocks)


def ensure_overlays_enabled():
    """Ensures that the pyro marker overlay is enabled after loading a file."""
    pyro_control = bpy.context.scene.skybrush.pyro_control
    pyro_control.ensure_overlays_enabled_if_needed()


def run_tasks_post_load(*args):
    """Runs all the tasks that should be completed after loading a file."""
    ensure_overlays_enabled()


@contextmanager
def suspended_pyro_effects() -> Iterator[None]:
    """Context manager that suspends pyro marker overlay when the context is entered
    and re-enables them when the context is exited.
    """
    global _suspension_counter
    _suspension_counter += 1
    try:
        yield
    finally:
        _suspension_counter -= 1


class PyroEffectsTask(Task):
    """Background task that is invoked after every frame change and that
    updates pyro overlay markers if needed.
    """

    functions = {
        "depsgraph_update_post": run_update_pyro_overlay_markers,
        "frame_change_post": run_update_pyro_overlay_markers,
        "load_post": run_tasks_post_load,
    }
