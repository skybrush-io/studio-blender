from sbstudio.api import SkybrushStudioAPI

__all__ = ("api",)

#: One singleton API object that the entire Blender plugin uses to talk to
#: Skybrush Studio
api = SkybrushStudioAPI()
