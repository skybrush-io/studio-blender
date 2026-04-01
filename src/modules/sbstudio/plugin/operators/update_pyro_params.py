from bpy.types import Operator

from sbstudio.plugin.selection import get_selected_drones
from sbstudio.plugin.utils.pyro_markers import get_pyro_markers_of_object
from sbstudio.plugin.views import find_all_3d_views_and_their_areas

__all__ = ("UpdatePyroParamsFromSelectedDroneOperator",)


class UpdatePyroParamsFromSelectedDroneOperator(Operator):
    """Updates the pyro params of the pyro panel from the currently
    selected drone and pyro channel."""

    bl_idname = "skybrush.update_pyro_params_from_selection"
    bl_label = "Update Pyro Params from Selected Drone"
    bl_description = (
        "Updates the pyro parameters from the currently selected drone and pyro channel"
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        # This code path is invoked after an undo-redo
        return {"FINISHED"} if self._run(context) else {"CANCELLED"}

    def _run(self, context):
        # get selected drone
        selection = get_selected_drones()
        if len(selection) != 1:
            self.report({"ERROR"}, "Select a single drone to update pyro params")
            return False
        drone = selection[0]

        # get currently selected channel
        pyro_control = context.scene.skybrush.pyro_control
        channel = pyro_control.channel

        # get pyro payload of drone
        marker = get_pyro_markers_of_object(drone).markers.get(channel)
        if marker is None:
            self.report(
                {"ERROR"},
                f"The selected drone does not trigger pyro on channel {channel}",
            )
            return False

        # update pyro control params
        pyro_control.update_params_from_pyro_payload(marker.payload)

        # Mark all the 3D views to be redrawn
        for _, area in find_all_3d_views_and_their_areas():
            area.tag_redraw()

        return True
