import threading

import bpy
from bpy.props import BoolProperty
from bpy.types import Context, Operator

from sbstudio.model.safety_check import SafetyCheckParams
from sbstudio.plugin.api import call_api_from_blender_operator
from sbstudio.plugin.props.frame_range import FrameRangeProperty, resolve_frame_range
from sbstudio.plugin.tasks.light_effects import suspended_light_effects
from sbstudio.plugin.tasks.safety_check import suspended_safety_checks
from sbstudio.plugin.utils.sampling import sample_positions_of_objects_in_frame_range
from sbstudio.viewer_bridge import (
    SkybrushViewerBridge,
    SkybrushViewerError,
    SkybrushViewerNotFoundError,
)

from .utils import get_drones_to_export

__all__ = ("ValidateTrajectoriesOperator",)

skybrush_viewer = SkybrushViewerBridge()
"""Global object to access Skybrush Viewer and send it the trajectories to validate."""


class ValidateTrajectoriesOperator(Operator):
    """Validates the trajectories of the drones in a given frame range."""

    bl_idname = "skybrush.validate_trajectories"
    bl_label = "Validate Trajectories"
    bl_description = "Validates the trajectories of the drones in a given frame range."

    # validate all drones or only selected ones
    selected_only = BoolProperty(
        name="Selection only",
        default=False,
        description=(
            "Validate only the selected drones. "
            "Uncheck to export all drones, irrespectively of the selection."
        ),
    )

    # frame range source
    frame_range = FrameRangeProperty()

    def execute(self, context: Context):
        drones = get_drones_to_export(selected_only=self.selected_only)
        frame_range = resolve_frame_range(self.frame_range)
        if frame_range is None:
            self.report({"ERROR"}, "Selected frame range is empty")
            return {"CANCELLED"}

        safety_check = context.scene.skybrush.safety_check
        validation = SafetyCheckParams(
            max_velocity_xy=(
                safety_check.velocity_xy_warning_threshold if safety_check else 8
            ),
            max_velocity_z=(
                safety_check.velocity_z_warning_threshold if safety_check else 2
            ),
            max_velocity_z_up=(
                safety_check.velocity_z_warning_threshold_up_or_none
                if safety_check
                else None
            ),
            max_acceleration=(
                safety_check.acceleration_warning_threshold if safety_check else 4
            ),
            max_yaw_rate=safety_check.yaw_rate_warning_threshold
            if safety_check
            else 30,
            max_altitude=(
                safety_check.altitude_warning_threshold if safety_check else 150
            ),
            min_distance=(
                safety_check.proximity_warning_threshold if safety_check else 3
            ),
        )

        try:
            running = skybrush_viewer.check_running()
        except SkybrushViewerNotFoundError:
            running = False
        except SkybrushViewerError as ex:
            self.report({"ERROR"}, str(ex))
            return {"CANCELLED"}
        except Exception:
            self.report(
                {"ERROR"}, "Error while checking whether Skybrush Viewer is running"
            )
            return {"CANCELLED"}

        if not running:
            self.report(
                {"ERROR"},
                "Skybrush Viewer is not running; please start it and try again",
            )
            return {"CANCELLED"}

        with suspended_safety_checks(), suspended_light_effects():
            trajectories = sample_positions_of_objects_in_frame_range(
                drones,
                frame_range,
                fps=4,
                context=context,
                simplify=True,
            )

        # Calculate the start time of the validated range, in seconds
        fps = context.scene.render.fps
        start_of_scene = context.scene.frame_start
        timestamp_offset = (frame_range[0] - start_of_scene) / fps

        if timestamp_offset:
            for trajectory in trajectories.values():
                trajectory.shift_time_in_place(-timestamp_offset)

        filename = bpy.data.filepath or None
        try:
            with call_api_from_blender_operator(self) as api:
                show_data = api.export(
                    trajectories=trajectories,
                    validation=validation,
                    timestamp_offset=(
                        timestamp_offset if timestamp_offset != 0 else None
                    ),
                    renderer="skyc",
                )
        except Exception:
            return {"CANCELLED"}

        assert show_data is not None

        # A load may be cancelled from modal(); the worker checks this before
        # sending so a cancelled show is never posted after the operator exits.
        self._cancelled = threading.Event()

        if context.window is None:
            # No window to attach a modal handler to, e.g. when invoked from
            # the Python console; run the load synchronously so the caller
            # still gets the outcome instead of a thread without a report.
            self._load_show_in_background(show_data, filename)
            status, message = self._load_outcome
            self.report({"INFO"} if status == "FINISHED" else {"ERROR"}, message)
            return {status}

        # Send the show to the Viewer in a background thread so the Blender UI
        # stays responsive while the request is in flight.
        self._load_outcome = None
        self._load_thread = threading.Thread(
            target=self._load_show_in_background,
            args=(show_data, filename),
            daemon=True,
        )
        self._load_thread.start()
        self._load_timer = context.window_manager.event_timer_add(
            0.1, window=context.window
        )
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context: Context, event):
        if event.type == "TIMER":
            if not self._load_thread.is_alive():
                context.window_manager.event_timer_remove(self._load_timer)
                status, message = self._load_outcome
                self.report({"INFO"} if status == "FINISHED" else {"ERROR"}, message)
                return {status}
        elif event.type == "ESC":
            self._cancelled.set()
            context.window_manager.event_timer_remove(self._load_timer)
            return {"CANCELLED"}
        return {"RUNNING_MODAL", "PASS_THROUGH"}

    def _load_show_in_background(self, show_data: bytes, filename):
        cancelled = getattr(self, "_cancelled", None)
        if cancelled is not None and cancelled.is_set():
            self._load_outcome = ("CANCELLED", "Validation cancelled")
            return
        try:
            skybrush_viewer.load_show_for_validation(show_data, filename=filename)
            self._load_outcome = (
                "FINISHED",
                "Now switch to the Skybrush Viewer window to view the results",
            )
        except SkybrushViewerNotFoundError:
            self._load_outcome = (
                "CANCELLED",
                "Skybrush Viewer is not running; please start it and try again",
            )
        except SkybrushViewerError as ex:
            self._load_outcome = ("CANCELLED", str(ex))
        except Exception:
            self._load_outcome = (
                "CANCELLED",
                "Error while sending show data to Skybrush Viewer",
            )

    def invoke(self, context: Context, event):
        return context.window_manager.invoke_props_dialog(self)
