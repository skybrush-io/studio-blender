from bpy.props import BoolProperty
from bpy.types import Operator

from sbstudio.plugin.api import get_api
from sbstudio.plugin.props import FrameRangeProperty
from sbstudio.plugin.utils import (
    get_temporary_directory,
    open_file_with_default_application,
)
from sbstudio.plugin.utils.sampling import sample_positions_of_objects_in_frame_range

from .export_to_skyc import get_drones_to_export, resolve_frame_range

__all__ = ("ValidateTrajectoriesOperator",)


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
        # TODO(ntamas): allow the user to choose the frame range and the selection

        drones = get_drones_to_export(selected_only=self.selected_only)
        frame_range = resolve_frame_range(self.frame_range)

        trajectories = sample_positions_of_objects_in_frame_range(
            drones,
            frame_range,
            fps=4,
            context=context,
            by_name=True,
        )

        output = get_temporary_directory() / "validation.pdf"
        try:
            get_api().generate_plots(trajectories=trajectories, output=output)
        except Exception:
            self.report(
                {"ERROR"},
                "Error while invoking plot generation on the Skybrush Studio online service",
            )
            return {"FINISHED"}

        if output.exists():
            open_file_with_default_application(output)
        else:
            self.report(
                {"ERROR"},
                "Could not save generated plot from the Skybrush Studio online service",
            )

        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
