"""Native video frames and view projection for drone LED colors."""

from dataclasses import dataclass
from fractions import Fraction
from math import ceil, floor, isfinite, ulp
from pathlib import Path

import bpy
import numpy as np

from .uv_sampling import sample_pixels_clamped


@dataclass(frozen=True)
class VideoFrame:
    pixels: np.ndarray
    aspect: float
    srgb: bool


_cached_key = None
_cached_frame = None


def clear_video_frame():
    global _cached_key, _cached_frame
    _cached_key = _cached_frame = None


def _check_file(image):
    if not Path(bpy.path.abspath(image.filepath, library=image.library)).is_file():
        raise ValueError(f"找不到视频文件：{image.filepath}")


def _video_image(texture):
    image = texture.image if isinstance(texture, bpy.types.ImageTexture) else None
    if image is None or image.source != "MOVIE":
        raise ValueError("请重新选择视频文件")
    return image


def video_source_fps(texture):
    return float(texture.get("drones_anim_video_fps", 0.0)) if texture is not None else 0.0


def ensure_video_source_fps(texture):
    if video_source_fps(texture) > 0:
        return
    image = _video_image(texture)
    _check_file(image)
    filepath = bpy.path.abspath(image.filepath, library=image.library)
    try:
        clip = bpy.data.movieclips.load(filepath, check_existing=False)
    except RuntimeError as error:
        raise ValueError(f"无法读取视频帧率：{image.name}") from error
    try:
        fps = clip.fps
        if not isfinite(fps) or fps <= 0:
            raise ValueError(f"无法读取视频帧率：{image.name}")
        texture["drones_anim_video_fps"] = fps
    finally:
        bpy.data.movieclips.remove(clip)


def load_video(filepath):
    """Open a dedicated image and texture so other image users cannot seek it."""
    if not Path(filepath).is_file():
        raise ValueError(f"找不到视频文件：{filepath}")
    image = bpy.data.images.load(filepath, check_existing=False)
    texture = None
    try:
        if image.source != "MOVIE":
            raise ValueError("请选择 Blender 可读取的视频文件")
        texture = bpy.data.textures.new(name=f"视频投影：{image.name}", type="IMAGE")
        texture.image = image
        texture["drones_anim_video"] = True
        duration = image.frame_duration
        if duration < 1:
            raise ValueError("视频没有可读取的画面")
        ensure_video_source_fps(texture)
        read_video_frame(texture, 1)
        return texture, duration
    except Exception:
        if texture is not None:
            bpy.data.textures.remove(texture)
        bpy.data.images.remove(image)
        raise


def discard_unused_video(texture):
    if texture is None or texture.users or not texture.get("drones_anim_video"):
        return
    image = texture.image
    bpy.data.textures.remove(texture)
    if image is not None and image.users == 0:
        bpy.data.images.remove(image)


def read_video_frame(texture, frame):
    """Select the native image buffer with the texture's ImageUser."""
    global _cached_key, _cached_frame
    image = _video_image(texture)
    colorspace = image.colorspace_settings.name
    key = (texture.session_uid, image.session_uid, image.filepath, colorspace, frame)
    if key == _cached_key:
        return _cached_frame
    _check_file(image)
    texture.image_user.frame_current = frame
    # Evaluating the image texture makes its requested frame the Image pixel buffer.
    texture.evaluate((0.0, 0.0, 0.0))
    width, height = image.size
    channels = image.channels
    length = len(image.pixels)
    if width < 1 or height < 1 or channels != 4 or length != width * height * channels:
        raise ValueError(f"无法读取视频第 {frame} 帧：{image.name}")
    encoded_color = not image.is_float and not image.colorspace_settings.is_data
    if encoded_color and colorspace not in {"sRGB", "Linear", "Linear Rec.709"}:
        raise ValueError(f"不支持该视频色彩空间：{colorspace}")
    pixels = np.empty(length, dtype=np.float32)
    image.pixels.foreach_get(pixels)
    aspect_x, aspect_y = image.display_aspect
    aspect = width / height
    if aspect_x > 0 and aspect_y > 0:
        aspect *= aspect_x / aspect_y
    _cached_frame = VideoFrame(
        pixels.reshape(height, width, channels), aspect, encoded_color and colorspace == "sRGB"
    )
    _cached_key = key
    return _cached_frame


def _rate_fraction(value):
    # Recover common rates such as 30000/1001 from Blender's float32 metadata.
    exact = Fraction(value)
    common = exact.limit_denominator(1001)
    return common if abs(float(common) - value) <= value * 2**-24 else exact


def _source_frames_per_scene_frame(effect):
    fps = video_source_fps(effect.video_texture)
    if fps <= 0:
        return Fraction(1)
    render = effect.id_data.render
    return _rate_fraction(fps) * _rate_fraction(render.fps_base) / render.fps


def video_natural_end(effect):
    scene_frames = ceil(effect.video_duration / _source_frames_per_scene_frame(effect))
    return effect.video_start + max(0, scene_frames - 1)


def video_source_frame(effect, scene_frame):
    """Return the one-based source frame displayed at this scene time."""
    duration = effect.video_duration
    if not effect.video_enabled or not duration or not effect.video_start <= scene_frame < effect.video_end + 1:
        return None
    ratio = _source_frames_per_scene_frame(effect)
    position = (scene_frame - effect.video_start) * ratio
    # Blender stores the fractional part of a scene frame as float32.
    tolerance = float(ratio) * 2**-25 + 4 * ulp(float(position))
    nearest = round(position)
    index = nearest if abs(position - nearest) <= tolerance else floor(position)
    if index >= duration and (effect.video_end_locked or effect.video_end <= video_natural_end(effect)):
        return None
    return index % duration + 1


def video_is_active(effect, frame):
    return video_source_frame(effect, frame) is not None


def active_video_effects(settings, frame):
    if settings is None:
        return ()
    return tuple(effect for effect in settings.video_effects if video_is_active(effect, frame))


def validate_video_export(context, plan):
    settings = getattr(context.scene, "drones_anim_led", None)
    if settings is None:
        return
    for effect in settings.video_effects:
        if not effect.video_enabled or not any(video_is_active(effect, frame) for frame in plan):
            continue
        if bpy.app.background or context.window is None:
            raise ValueError("此范围包含视频灯效，请在 Blender 界面中导出 MAT")
        if not effect.video_view_captured:
            raise ValueError(f"{effect.name}：请先捕获投影视角")
        _check_file(_video_image(effect.video_texture))
        if video_source_fps(effect.video_texture) <= 0:
            raise ValueError(f"{effect.name}：请重新选择视频以读取素材帧率")


def project_uv(positions, view_matrix, viewport_size, aspect):
    """Return valid drone indices and UVs in the frame fitted to this formation."""
    positions = np.asarray(positions, dtype=np.float64).reshape(-1, 3)
    matrix = np.asarray(view_matrix, dtype=np.float64).reshape(4, 4)
    clip = positions @ matrix[:, :3].T + matrix[:, 3]
    indices = np.flatnonzero(np.isfinite(clip).all(axis=1) & (clip[:, 3] > 1e-8))
    if not len(indices):
        return indices, np.empty((0, 2))
    screen = clip[indices, :2] / clip[indices, 3, None] * np.asarray(viewport_size)
    low, high = screen.min(axis=0), screen.max(axis=0)
    size = high - low
    if not size.any():
        return indices, np.full_like(screen, 0.5)
    center = low + size * 0.5
    fitted_width = max(size[0], size[1] * aspect)
    fitted_size = np.array((fitted_width, fitted_width / aspect))
    return indices, (screen - center) / fitted_size + 0.5


def projected_colors(effects, scene_frame, positions, base_colors, *, drones=None):
    """Apply lower-priority effects first over the original LED colors."""
    colors = np.array(base_colors, dtype=np.float64)
    positions = np.asarray(positions, dtype=np.float64)
    drone_indices = None
    for effect in reversed(effects):
        if not effect.video_view_captured:
            raise ValueError(f"{effect.name}：请先捕获投影视角")
        target_indices = None
        effect_positions = positions
        if effect.video_targets:
            if drone_indices is None:
                if drones is None:
                    raise ValueError("需要无人机对象来匹配视频灯效的影响范围")
                drone_indices = {drone: index for index, drone in enumerate(drones)}
            matching = [drone_indices.get(target.drone) for target in effect.video_targets]
            target_indices = np.array(
                [index for index in matching if index is not None], dtype=np.intp
            )
            if not len(target_indices):
                continue
            effect_positions = positions[target_indices]
        source_frame = video_source_frame(effect, scene_frame)
        if source_frame is None:
            continue
        if video_source_fps(effect.video_texture) <= 0:
            _check_file(_video_image(effect.video_texture))
            raise ValueError(f"{effect.name}：请重新选择视频以读取素材帧率")
        video_frame = read_video_frame(effect.video_texture, source_frame)
        indices, uv = project_uv(
            effect_positions, effect.video_view_matrix, effect.video_viewport_size, video_frame.aspect
        )
        if target_indices is not None:
            indices = target_indices[indices]
        colors[indices, :3] = sample_pixels_clamped(
            video_frame.pixels, uv, srgb=video_frame.srgb
        )
    return colors
