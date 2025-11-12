import logging
import webbrowser

from bpy.types import Operator

__all__ = ("RegisterHardwareIDOperator",)


#############################################################################
# configure logger

log = logging.getLogger(__name__)


SKYBRUSH_ACCOUNT_URL_TEMPLATE = """https://account.skybrush.io/go/register-hardware-id?hardwareId={hardware_id}&product=io.skybrush.studio.api"""


class RegisterHardwareIDOperator(Operator):
    """Opens Skybrush account in the default browser to register a given hardware ID."""

    bl_idname = "skybrush.register_hardware_id"
    bl_label = "Register HWID"
    bl_description = "Open Skybrush account to register your hardware ID"

    def execute(self, context):
        from sbstudio.plugin.model.global_settings import get_preferences

        prefs = get_preferences()
        hardware_id = prefs.hardware_id

        if hardware_id:
            webbrowser.open(
                SKYBRUSH_ACCOUNT_URL_TEMPLATE.format(hardware_id=hardware_id)
            )

        return {"FINISHED"}
