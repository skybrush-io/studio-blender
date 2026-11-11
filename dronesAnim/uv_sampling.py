"""Sample an explicit UV image at Drone Anim's attached mesh vertices."""

from array import array
from math import floor, isfinite


def _linear_channel(value):
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def sample_pixel(pixels, width, height, uv, *, repeat=True, srgb=False):
    """Bilinear RGBA sampling with Blender's bottom-left image origin."""
    u, v = uv
    if not (isfinite(u) and isfinite(v)):
        raise ValueError("UV 贴图包含非有限数值坐标")
    if repeat:
        u, v = u % 1.0, v % 1.0
    else:
        u, v = min(1.0, max(0.0, u)), min(1.0, max(0.0, v))
    x, y = u * width - 0.5, v * height - 0.5
    x0, y0 = floor(x), floor(y)
    tx, ty = x - x0, y - y0

    def pixel(ix, iy):
        if repeat:
            ix, iy = ix % width, iy % height
        else:
            ix, iy = min(width - 1, max(0, ix)), min(height - 1, max(0, iy))
        offset = (iy * width + ix) * 4
        rgb = pixels[offset : offset + 3]
        # Filter in linear space, not in the image's sRGB encoding.
        return tuple(_linear_channel(c) for c in rgb) if srgb else tuple(rgb)

    corners = (
        (pixel(x0, y0), (1 - tx) * (1 - ty)),
        (pixel(x0 + 1, y0), tx * (1 - ty)),
        (pixel(x0, y0 + 1), (1 - tx) * ty),
        (pixel(x0 + 1, y0 + 1), tx * ty),
    )
    return tuple(
        min(1.0, max(0.0, sum(rgb[channel] * weight for rgb, weight in corners)))
        for channel in range(3)
    )


def sample_pixels_clamped(pixels, uv, *, srgb=False):
    """Batch equivalent of sample_pixel for bottom-left RGBA arrays."""
    import numpy as np

    height, width = pixels.shape[:2]
    coords = np.clip(uv, 0.0, 1.0) * (width, height) - 0.5
    base = np.floor(coords).astype(np.intp)
    weights = coords - base
    rgb = np.zeros((len(uv), 3))
    for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
        x = np.clip(base[:, 0] + dx, 0, width - 1)
        y = np.clip(base[:, 1] + dy, 0, height - 1)
        corner = pixels[y, x, :3].astype(np.float64)
        if srgb:
            corner = np.where(corner <= 0.04045, corner / 12.92, ((corner + 0.055) / 1.055) ** 2.4)
        wx = weights[:, 0] if dx else 1 - weights[:, 0]
        wy = weights[:, 1] if dy else 1 - weights[:, 1]
        rgb += corner * (wx * wy)[:, None]
    return np.clip(rgb, 0.0, 1.0)


def _attachment(drone):
    constraint = next(
        (
            item
            for item in drone.constraints
            if item.type == "COPY_LOCATION" and item.name == "Drone Anim Vertex"
        ),
        None,
    )
    if (
        constraint is None
        or constraint.target is None
        or constraint.target.type != "MESH"
        or constraint.mute
        or constraint.influence != 1.0
        or constraint.use_offset
        or not all((constraint.use_x, constraint.use_y, constraint.use_z))
    ):
        raise ValueError(f"{drone.name}：没有启用完整的顶点附着约束")
    source = constraint.target
    index = drone.get("drones_anim_vertex_index")
    if not isinstance(index, int) or not 0 <= index < len(source.data.vertices):
        raise ValueError(f"{drone.name}：附着顶点索引无效")
    group = source.vertex_groups.get(constraint.subtarget)
    if group is None:
        raise ValueError(f"{drone.name}：缺少附着顶点组")
    return source, index, group.index


def sample_attached_colors(drones, image, depsgraph, *, uv_map="", repeat=True):
    """Validate and collect all colors before the operator changes any keys."""
    if image is None:
        raise ValueError("请先选择 UV 纹理图像")
    if image.source not in {"FILE", "GENERATED"}:
        raise ValueError("请使用单张静态图像；暂不支持视频、图像序列或 UDIM 分块纹理")
    width, height = image.size
    if width < 1 or height < 1 or len(image.pixels) != width * height * 4:
        raise ValueError("图像必须包含已加载的 RGBA 像素数据")
    colorspace = image.colorspace_settings.name
    if not image.is_float and colorspace not in {
        "sRGB",
        "Non-Color",
        "Raw",
        "Linear",
        "Linear Rec.709",
    }:
        raise ValueError(f"不支持该图像色彩空间：{colorspace}")
    pixels = array("f", [0.0]) * (width * height * 4)
    image.pixels.foreach_get(pixels)
    srgb = not image.is_float and colorspace == "sRGB"
    sources = {}
    for drone in drones:
        source, index, group_index = _attachment(drone)
        sources.setdefault(source, []).append((drone, index, group_index))
    result = []
    for source, entries in sources.items():
        members = {}
        for vertex in source.data.vertices:
            for group in vertex.groups:
                if group.weight > 0:
                    members.setdefault(group.group, []).append(vertex.index)
        for drone, index, group_index in entries:
            if members.get(group_index) != [index]:
                raise ValueError(
                    f"{drone.name}：附着顶点组必须仅包含该无人机标记的顶点"
                )
        evaluated = source.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
        try:
            original = source.data
            if (
                len(mesh.vertices) != len(original.vertices)
                or len(mesh.loops) != len(original.loops)
                or any(
                    a.vertex_index != b.vertex_index
                    for a, b in zip(mesh.loops, original.loops)
                )
            ):
                raise ValueError(f"{source.name}：修改器改变了附着网格的拓扑结构")
            layer = (
                mesh.uv_layers.get(uv_map)
                if uv_map
                else next(
                    (layer for layer in mesh.uv_layers if layer.active_render),
                    mesh.uv_layers.active,
                )
            )
            if layer is None:
                raise ValueError(
                    f"{source.name}：缺少 UV 贴图 {uv_map or '（活动渲染 UV）'}"
                )
            # UVs belong to face corners. A seam uses the first connected corner.
            first_loops = {}
            for loop in mesh.loops:
                first_loops.setdefault(loop.vertex_index, loop.index)
            for drone, index, _group_index in entries:
                if index not in first_loops:
                    raise ValueError(f"{drone.name}：附着顶点没有带 UV 坐标的相邻面")
                uv = layer.data[first_loops[index]].uv
                result.append(
                    (
                        drone,
                        sample_pixel(
                            pixels, width, height, uv, repeat=repeat, srgb=srgb
                        ),
                    )
                )
        finally:
            evaluated.to_mesh_clear()
    return result
