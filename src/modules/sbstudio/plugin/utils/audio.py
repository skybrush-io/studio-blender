from bpy.path import abspath
from bpy.types import Context

from sbstudio.model.audio import Audio

__all__ = ("get_audio_from_context",)


def get_audio_from_context(context: Context) -> Audio | None:
    """Get the parameters of the first audio file embedded in the VSE
    of Blender.

    Args:
        context: the main Blender context

    Returns:
        the audio object parsed from VSE, or None if such object does not exist
    """
    sequence_editor = context.scene.sequence_editor
    if not sequence_editor:
        return None

    for strip in sequence_editor.strips.values():
        if (
            strip.type == "SOUND"
            and strip.sound
            and strip.sound.filepath.lower().endswith(".mp3")
        ):
            file_path = abspath(strip.sound.filepath)
            fps = context.scene.render.fps
            start_time = strip.frame_start / fps

            return Audio(file_path=file_path, start_time=start_time)

    return None
