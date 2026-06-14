from __future__ import annotations

import logging
from typing import Literal, cast

from bpy.props import BoolProperty, EnumProperty, StringProperty
from bpy.types import AddonPreferences, Context

from sbstudio.plugin.gateway import get_gateway
from sbstudio.plugin.operators.register_hardware_id import RegisterHardwareIDOperator
from sbstudio.plugin.operators.set_gateway_url import SetGatewayURLOperator
from sbstudio.plugin.operators.set_server_url import SetServerURLOperator
from sbstudio.plugin.utils import with_context

__all__ = ("DroneShowAddonGlobalSettings",)

#############################################################################
# configure logger

log = logging.getLogger(__name__)


def gateway_url_updated(
    self: DroneShowAddonGlobalSettings, context: Context | None = None
):
    """Callback that is called when the user updates the gateway URL in the add-on
    preferences.

    Tries to retrieve the hardware ID from the gateway and updates the hardware ID field
    in the preferences accordingly.
    """
    hardware_id: str = ""
    if self.gateway_url:
        try:
            gateway = get_gateway()
            hardware_id = gateway.get_hardware_id()
        except Exception as ex:
            log.warning(
                f"Studio gateway could not be reached at {self.gateway_url}: {ex}"
            )

    self.hardware_id = hardware_id


class DroneShowAddonGlobalSettings(AddonPreferences):
    """Global settings of the Skybrush Studio addon.

    This is active only when the addon is installed in the Blender add-on manager,
    not when it is provided to Blender dynamically at startup.
    """

    bl_idname = "ui_skybrush_studio"

    operation_mode: Literal["COMMUNITY", "LOCAL", "CLOUD", "ADVANCED"] = EnumProperty(
        name="Mode of operation",
        description=(
            "Specifies whether the user wishes to use the add-on with the community "
            "server, a local server instance or the cloud version with hardware ID "
            "based authentication"
        ),
        items=[
            (
                "COMMUNITY",
                "Community server",
                "Provided to the community for free. Limited drone count, no guaranteed uptime",
            ),
            (
                "LOCAL",
                "Local Skybrush Studio Server",
                "Skybrush Studio Server running on the same machine as Blender itself. License required",
            ),
            (
                "CLOUD",
                "Skybrush Studio Cloud (experimental)",
                "Skybrush Studio Server in the cloud, with hardware ID based authentication. License required",
            ),
            (
                "ADVANCED",
                "Advanced setup",
                "Fully customizable settings settings, for experts only. No support provided",
            ),
        ],
        default="COMMUNITY",
    )

    # license_file is unused, kept for backward compatibility purposes only
    license_file: str = StringProperty(
        name="License file",
        description="Full path to the license file to be used as the API key",
        subtype="FILE_PATH",
    )

    hardware_id: str = StringProperty(
        name="Hardware ID",
        description="Hardware ID of the computer running Skybrush Studio for Blender",
    )

    api_key: str = StringProperty(
        name="API Key",
        description=(
            "API key that is used when communicating with the Skybrush Studio "
            "server. Leave empty if you do not know what it is"
        ),
    )

    server_url: str = StringProperty(
        name="Server URL",
        description=(
            "URL of a dedicated Skybrush Studio server if you are using a "
            "local server. Leave it empty to use the cloud server provided "
            "for the community for free and for pro users with signed requests"
        ),
    )

    gateway_url: str = StringProperty(
        name="Gateway URL",
        description=(
            "URL of a dedicated Skybrush Studio Gateway for using the online "
            "cloud server with pro features. Leave it empty if you have a local "
            "server or if you wish to use the free community cloud server"
        ),
        update=gateway_url_updated,
    )

    enable_experimental_features: bool = BoolProperty(
        name="Enable experimental features",
        description=(
            "Whether to enable experimental features in the add-on. Experimental "
            "features are currently in a testing phase and may be changed, "
            "disabled or removed in future versions without notice"
        ),
        default=False,
    )

    def draw(self, context: Context) -> None:
        layout = self.layout

        # Header: mode of operation. Most other widgets depend on this.
        mode = self.operation_mode
        if mode not in ("COMMUNITY", "LOCAL", "CLOUD", "ADVANCED"):
            # Failsafe in case the user somehow managed to screw up this setting
            mode = "ADVANCED"
        layout.prop(self, "operation_mode")

        # Top separator not needed for the simple cases
        if mode not in ("COMMUNITY", "LOCAL"):
            layout.separator()

        # Hardware ID and register button. Needed for the cloud-based solution only.
        if mode in ("CLOUD", "ADVANCED"):
            self._draw_hardware_id_widgets()

        # Gateway URL. Only for advanced use-cases. Gateway URL implied for "CLOUD"
        # and empty for all other configurations.
        if mode == "ADVANCED":
            self._draw_gateway_widgets()

        # API key. Not needed for local servers.
        if mode != "LOCAL":
            layout.prop(self, "api_key")

        # Server URL and shortcuts to set to predefined values. Only for advanced use-cases.
        if mode == "ADVANCED":
            self._draw_server_url_widgets()

        # Bottom separator not needed for the simple cases
        if mode not in ("COMMUNITY", "LOCAL"):
            layout.separator()

        layout.prop(self, "enable_experimental_features")

    def _draw_hardware_id_widgets(self) -> None:
        layout = self.layout

        row = layout.row()
        col = row.column()
        col.enabled = False
        col.prop(self, "hardware_id")

        col = row.column()
        col.scale_x = 0.4
        col.enabled = bool(self.hardware_id)
        col.operator(RegisterHardwareIDOperator.bl_idname, text="Register")

    def _draw_gateway_widgets(self) -> None:
        layout = self.layout

        row = layout.row()
        col = row.column()
        col.prop(self, "gateway_url")

        col = row.column()
        col.scale_x = 0.4
        col.label(text="")  # intentionally left empty for alignment

        row = layout.row()
        op: SetGatewayURLOperator = row.operator(
            SetGatewayURLOperator.bl_idname, text="Use local gateway"
        )
        op.url = "http://localhost:7999"

        op: SetGatewayURLOperator = row.operator(
            SetGatewayURLOperator.bl_idname, text="Do not use gateway"
        )
        op.url = ""

        layout.separator()

    def _draw_server_url_widgets(self) -> None:
        layout = self.layout

        layout.prop(self, "server_url")

        row = layout.row()
        op: SetServerURLOperator = row.operator(
            SetServerURLOperator.bl_idname, text="Use local server"
        )
        op.url = "http://localhost:8000"

        op: SetServerURLOperator = row.operator(
            SetServerURLOperator.bl_idname, text="Use community server"
        )
        op.url = ""


@with_context
def get_preferences(context: Context | None = None) -> DroneShowAddonGlobalSettings:
    """Helper function to retrieve the preferences of the add-on from the
    given context object.
    """
    assert context is not None
    prefs = context.preferences
    addon_prefs = prefs.addons[DroneShowAddonGlobalSettings.bl_idname].preferences
    return cast(DroneShowAddonGlobalSettings, addon_prefs)
