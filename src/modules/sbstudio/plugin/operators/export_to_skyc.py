from typing import Any

import bpy
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    StringProperty,
)

from sbstudio.export_policy import CHECKED, DEFAULT_MAX_EXPORT_DEVIATION
from sbstudio.model.file_formats import FileFormat

from .base import ExportOperator

__all__ = ("SkybrushExportOperator",)


def _export_policy_updated(self, context):
    from sbstudio.plugin.model.global_settings import get_preferences

    # RNA updates also run while bpy.ops keyword arguments are being assigned.
    # Only the interactive file-browser policy switch may reset explicit ranges.
    if (
        self.export_policy == CHECKED
        and get_preferences().operation_mode == "OFFLINE"
        and context is not None
        and context.space_data is not None
        and context.space_data.type == "FILE_BROWSER"
    ):
        self.export_selected = False
        self.frame_range = "STORYBOARD"


#############################################################################
# Operator that allows the user to invoke the .skyc export operation
#############################################################################


class SkybrushExportOperator(ExportOperator):
    """Export trajectories and lights to a compiled Skybrush show (.skyc)."""

    bl_idname = "export_scene.skybrush"
    bl_label = "Export Skybrush Show"
    bl_description = "Export a Skybrush show; offline mode produces a draft requiring independent flight review"
    bl_options = {"REGISTER"}

    # List of file extensions that correspond to Skybrush files
    filter_glob = StringProperty(default="*.skyc", options={"HIDDEN"})
    filename_ext = ".skyc"

    export_policy = EnumProperty(
        name="Offline export",
        items=[
            (
                "CHECKED",
                "Checked draft",
                "Require full storyboard, all drones, dense audit and passing implemented checks; not flight approval",
            ),
            (
                "PREVIEW",
                "Preview only",
                "Allow unfinished designs and validation warnings for inspection; not for flight",
            ),
        ],
        default=CHECKED,
        update=_export_policy_updated,
    )

    max_export_deviation = FloatProperty(
        name="Export tolerance (m)",
        description="Maximum sampled difference between Blender motion and exported paths; authoring fidelity only, not a flight tracking margin",
        default=DEFAULT_MAX_EXPORT_DEVIATION,
        min=0.001,
        precision=3,
    )

    background_export = BoolProperty(
        name="Background export",
        description="Export a temporary scene snapshot in another Blender process; press Esc to cancel. Snapshot creation itself is synchronous",
        default=False,
    )

    def execute(self, context):
        from sbstudio.plugin.model.global_settings import get_preferences

        if (
            get_preferences().operation_mode == "OFFLINE"
            and self.export_policy == CHECKED
            and not self.properties.is_property_set("frame_range")
        ):
            self.frame_range = "STORYBOARD"

        if (
            get_preferences().operation_mode == "OFFLINE"
            and self.background_export
            and not bpy.app.background
        ):
            from .native_background import start

            return start(self, context)
        return super().execute(context)

    def modal(self, context, event):
        from .native_background import modal

        return modal(self, context, event)

    def cancel(self, context):
        from .native_background import cleanup

        cleanup(self, context)

    def invoke(self, context, event):
        from sbstudio.plugin.model.global_settings import get_preferences

        # A preview exception from an earlier dialog must not silently become
        # the next designer's default export policy.
        if get_preferences().operation_mode == "OFFLINE":
            self.export_policy = CHECKED
            self.export_selected = False
            self.frame_range = "STORYBOARD"
        return super().invoke(context, event)

    audit_motion = BoolProperty(
        name="Dense motion audit",
        description="Sample evaluated positions every half-frame and include diagnostics; slower and not a continuous safety guarantee",
        default=False,
    )

    # output trajectory frame rate
    output_fps = IntProperty(
        name="Trajectory FPS",
        default=4,
        min=1,
        description="Number of samples to take from trajectories per second",
    )

    # output light program frame rate
    light_output_fps = IntProperty(
        name="Light FPS",
        default=4,
        min=1,
        description="Number of samples to take from light programs per second",
    )

    # pyro control enable/disable
    use_pyro_control = BoolProperty(
        name="Export pyro (PRO)",
        description="Specifies whether the pyro program of each drone should be included in the show",
        default=False,
    )

    # yaw control enable/disable
    use_yaw_control = BoolProperty(
        name="Export yaw (PRO)",
        description="Specifies whether the yaw angle of each drone should be controlled during the show",
        default=False,
    )

    # audio export enable/disable
    export_audio = BoolProperty(
        name="Export audio",
        description="Specifies whether a single audio file in the VSE should be exported into the show file",
        default=False,
    )

    # camera export enable/disable
    export_cameras = BoolProperty(
        name="Export cameras",
        description="Specifies whether cameras defined in Blender should be exported into the show file",
        default=False,
    )

    def draw(self, context):
        from sbstudio.plugin.model.global_settings import get_preferences

        layout = self.layout
        layout.use_property_split = True

        offline = get_preferences().operation_mode == "OFFLINE"
        checked = offline and self.export_policy == CHECKED
        if offline:
            layout.prop(self, "export_policy")
            box = layout.box()
            box.label(text="Flight review still required", icon="ERROR")
            if checked:
                box.label(text="All drones / full storyboard")
                box.label(text="Half-frame motion audit required")
            else:
                box.label(text="PREVIEW ONLY - not for flight")
        column = layout.column()
        column.enabled = not checked
        column.prop(self, "export_selected")
        column.prop(self, "frame_range")
        layout.prop(self, "redraw")
        layout.prop(self, "output_fps")
        layout.prop(self, "light_output_fps")
        if offline:
            if not checked:
                layout.prop(self, "audit_motion")
            layout.prop(self, "max_export_deviation")
            layout.prop(self, "background_export")

        layout.separator()

        column = layout.column(align=True)
        column.prop(self, "export_audio")
        column.prop(self, "export_cameras")
        column.prop(self, "use_pyro_control")
        column.prop(self, "use_yaw_control")

    def get_format(self) -> FileFormat:
        return FileFormat.SKYC

    def get_operator_name(self) -> str:
        return ".skyc exporter"

    def get_settings(self) -> dict[str, Any]:
        return {
            "export_policy": self.export_policy,
            "max_export_deviation": self.max_export_deviation,
            "audit_motion": self.audit_motion,
            "output_fps": self.output_fps,
            "light_output_fps": self.light_output_fps,
            "use_pyro_control": self.use_pyro_control,
            "use_yaw_control": self.use_yaw_control,
            "export_audio": self.export_audio,
            "export_cameras": self.export_cameras,
        }
