from __future__ import annotations

import logging

from bpy.props import BoolProperty, StringProperty
from bpy.types import AddonPreferences, Context
from typing import Optional

from sbstudio.plugin.operators.register_hardware_id import RegisterHardwareIDOperator
from sbstudio.plugin.operators.set_server_url import SetServerURLOperator
from sbstudio.plugin.operators.set_gateway_url import SetGatewayURLOperator
from sbstudio.plugin.gateway import get_gateway
from sbstudio.plugin.utils import with_context


__all__ = ("DroneShowAddonGlobalSettings",)

#############################################################################
# configure logger

log = logging.getLogger(__name__)


def gateway_url_updated(
    self: DroneShowAddonGlobalSettings, context: Optional[Context] = None
):
    hardware_id: str = ""
    if self.gateway_url:
        try:
            gateway = get_gateway()
            hardware_id = gateway.get_hardware_id()
            log.info(f"Hardware ID: {hardware_id}")
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

    license_file = StringProperty(
        name="License file",
        description=(
            "Full path to the license file to be used as the API Key "
            "(this feature is currently not available)"
        ),
        subtype="FILE_PATH",
    )

    hardware_id = StringProperty(
        name="Hardware ID",
        description="Hardware ID of the computer running Skybrush Studio for Blender",
    )

    api_key = StringProperty(
        name="API Key",
        description="API Key that is used when communicating with the Skybrush Studio server",
    )

    server_url = StringProperty(
        name="Server URL",
        description=(
            "URL of a dedicated Skybrush Studio server if you are using a "
            "local server. Leave it empty to use the cloud server provided "
            "for the community for free and for pro users with signed requests"
        ),
    )

    gateway_url = StringProperty(
        name="Gateway URL",
        description=(
            "URL of a dedicated Skybrush Studio Gateway for using the online "
            "cloud server with pro features. Leave it empty if you have a local "
            "server or if you wish to use the free community cloud server"
        ),
        update=gateway_url_updated,
    )

    enable_experimental_features = BoolProperty(
        name="Enable experimental features",
        description=(
            "Whether to enable experimental features in the add-on. Experimental "
            "features are currently in a testing phase and may be changed, "
            "disabled or removed in future versions without notice"
        ),
        default=False,
    )

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        col = row.column()
        col.enabled = False
        col.prop(self, "hardware_id")

        col = row.column()
        col.scale_x = 0.75
        col.enabled = bool(self.hardware_id)
        op = col.operator(RegisterHardwareIDOperator.bl_idname)

        layout.prop(self, "gateway_url")

        row = layout.row()
        op = row.operator(SetGatewayURLOperator.bl_idname, text="Use local gateway")
        op.url = "http://localhost:7999"

        op = row.operator(SetGatewayURLOperator.bl_idname, text="Do not use gateway")
        op.url = ""

        layout.prop(self, "api_key")
        # layout.prop(self, "license_file")
        layout.prop(self, "server_url")

        row = layout.row()
        op = row.operator(SetServerURLOperator.bl_idname, text="Use local server")
        op.url = "http://localhost:8000"

        op = row.operator(SetServerURLOperator.bl_idname, text="Use community server")
        op.url = ""

        layout.prop(self, "enable_experimental_features")


@with_context
def get_preferences(context: Optional[Context] = None) -> DroneShowAddonGlobalSettings:
    """Helper function to retrieve the preferences of the add-on from the
    given context object.
    """
    assert context is not None
    prefs = context.preferences
    return prefs.addons[DroneShowAddonGlobalSettings.bl_idname].preferences
