import bpy
import logging

from bpy.props import StringProperty
from bpy.types import Operator

__all__ = ("SetGatewayURLOperator",)


#############################################################################
# configure logger

log = logging.getLogger(__name__)


class SetGatewayURLOperator(Operator):
    """Sets the Studio Gateway URL to a fixed value."""

    bl_idname = "skybrush.set_gateway_url"
    bl_label = "Set gateway URL"
    bl_description = "Sets the Studio Gateway URL to a fixed value"

    url = StringProperty(default="")

    def execute(self, context):
        from sbstudio.plugin.model.global_settings import get_preferences

        prefs = get_preferences()
        prefs.gateway_url = self.url

        bpy.ops.wm.save_userpref()

        return {"FINISHED"}
