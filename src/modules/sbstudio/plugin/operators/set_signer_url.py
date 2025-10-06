import bpy
import logging

from bpy.props import StringProperty
from bpy.types import Operator

from sbstudio.plugin.signer import get_signer

__all__ = ("SetSignerURLOperator",)


#############################################################################
# configure logger

log = logging.getLogger(__name__)


class SetSignerURLOperator(Operator):
    """Sets the request signer URL to a fixed value."""

    bl_idname = "skybrush.set_signer_url"
    bl_label = "Set signer URL"
    bl_description = "Sets the request signer URL to a fixed value"

    url = StringProperty(default="")

    def execute(self, context):
        from sbstudio.plugin.model.global_settings import get_preferences

        prefs = get_preferences()
        prefs.signer_url = self.url

        bpy.ops.wm.save_userpref()

        return {"FINISHED"}
