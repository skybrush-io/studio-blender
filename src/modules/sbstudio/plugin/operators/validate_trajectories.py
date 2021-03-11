from bpy.props import BoolProperty
from bpy.types import Operator

from sbstudio.model.safety_check import SafetyCheckParams
from sbstudio.plugin.api import get_api
from sbstudio.plugin.props import FrameRangeProperty
from sbstudio.plugin.utils.sampling import sample_positions_of_objects_in_frame_range
from sbstudio.viewer_bridge import (
    SkybrushViewerBridge,
    SkybrushViewerError,
    SkybrushViewerNotFoundError,
)

from .export_to_skyc import get_drones_to_export, resolve_frame_range

__all__ = ("ValidateTrajectoriesOperator",)

#: Global object to access Skybrush Viewer and send it the trajectories to validate
skybrush_viewer = SkybrushViewerBridge()


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

    def execute(self, context):
        drones = get_drones_to_export(selected_only=self.selected_only)
        frame_range = resolve_frame_range(self.frame_range)

        safety_check = getattr(context.scene.skybrush, "safety_check", None)
        validation = SafetyCheckParams(
            max_velocity_xy=safety_check.velocity_xy_warning_threshold
            if safety_check
            else 8,
            max_velocity_z=safety_check.velocity_z_warning_threshold
            if safety_check
            else 2,
            max_altitude=safety_check.altitude_warning_threshold
            if safety_check
            else 150,
            min_distance=safety_check.proximity_warning_threshold
            if safety_check
            else 3,
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

        # TODO(ntamas): temporarily suspend validation and light effects for
        # the duration of the sampling
        trajectories = sample_positions_of_objects_in_frame_range(
            drones,
            frame_range,
            fps=4,
            context=context,
            by_name=True,
        )

        # Calculate the start time of the validated range, in seconds
        fps = context.scene.render.fps
        start_of_scene = context.scene.frame_start
        timestamp_offset = (frame_range[0] - start_of_scene) / fps
        try:
            show_data = get_api().export_to_skyc(
                trajectories=trajectories,
                validation=validation,
                timestamp_offset=timestamp_offset if timestamp_offset != 0 else None,
            )
        except Exception:
            self.report(
                {"ERROR"},
                "Error while invoking function on the Skybrush Studio online service",
            )
            return {"CANCELLED"}

        try:
            skybrush_viewer.load_show_for_validation(show_data)
            self.report(
                {"INFO"},
                "Now switch to the Skybrush Viewer window to view the results",
            )
            return {"FINISHED"}
        except SkybrushViewerNotFoundError:
            self.report(
                {"ERROR"},
                "Skybrush Viewer is not running; please start it and try again",
            )
        except SkybrushViewerError as ex:
            self.report({"ERROR"}, str(ex))
        except Exception:
            self.report({"ERROR"}, "Error while sending show data to Skybrush Viewer")

        return {"CANCELLED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
