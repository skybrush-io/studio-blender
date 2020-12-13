from sbstudio.api import SkybrushStudioAPI

__all__ = ("api",)

#: One singleton API object that the entire Blender plugin uses to talk to
#: Skybrush Studio
api = SkybrushStudioAPI()

# This is bad practice, but the default installation of Blender does not find
# the SSL certificates on macOS and there are reports about similar problems
# on Windows as well
# TODO(ntamas): sort this out!
api._skip_ssl_checks()
