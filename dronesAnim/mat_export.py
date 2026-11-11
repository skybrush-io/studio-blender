"""Scene export and dependency-free Level 5 MAT writing."""

import os
import re
import struct
import sys
import tempfile
from array import array
from dataclasses import dataclass
from math import floor
from pathlib import Path

from .sampling import SamplingPlan, sampling_plan


def _element(data_type, data):
    """Build a MAT data element."""
    return (
        struct.pack("<II", data_type, len(data))    # [Type:4B] [Size:4B]
        + data                                      # [Payload:Size B]
        + b"\0" * (-len(data) % 8)                  # [Padding:0-7B]
    )


def write_mat(stream, rows, columns, samples):
    """Write six matrices and zero-based Qn indices matching coordinate rows."""
    count = rows * columns
    if rows <= 0 or columns <= 0:
        raise ValueError("无人机数量和帧数必须大于零")
    if set(samples) != set("xyzrgb") or any(
        len(values) != count for values in samples.values()
    ):
        raise ValueError("坐标或颜色矩阵尺寸不一致")
    if rows > 0x7FFFFFFF or columns > 0x7FFFFFFF or count * 8 + 64 >= 2**31:
        raise ValueError("矩阵过大，超出当前 MAT 格式限制")
    if any(values.typecode != "d" or values.itemsize != 8 for values in samples.values()):
        raise ValueError("坐标和颜色必须使用八字节 double 数组")

    header = b"MATLAB 5.0 MAT-file, Created by Drone Animations"
    stream.write(
        header.ljust(116, b" ")     # [Description:116B]
        + b"\0" * 8                 # [Subsystem offset:8B]
        + struct.pack("<H", 0x0100) # [Version:2B]
        + b"IM"                     # [Endian:2B]
    )
    for name in ("r", "b", "g", "x", "y", "z", "Qn"):
        is_index = name == "Qn"
        matrix_columns = 1 if is_index else columns
        matrix_count = rows * matrix_columns
        metadata = (
            _element(6, struct.pack("<II", 6, 0))                 # [Class:4B] [Reserved:4B]; double=6
            + _element(5, struct.pack("<ii", rows, matrix_columns)) # [Rows:4B] [Columns:4B]
            + _element(1, name.encode("ascii"))                   # [Name:1-2B] [Padding:6-7B]
        )
        byte_count = matrix_count * 8
        padding = -byte_count % 8
        stream.write(struct.pack("<II", 14, len(metadata) + 8 + byte_count + padding))  # [Matrix type:4B] [Content size:4B]
        stream.write(metadata)
        stream.write(struct.pack("<II", 9, byte_count))                               # [Storage type:4B] [Data size:4B]; double=9
        if is_index:
            # One index per drone, in the same order as coordinate rows.
            for start in range(0, rows, 8192):
                indices = range(start, min(start + 8192, rows))
                stream.write(struct.pack("<" + "d" * len(indices), *indices)) # [Index:8B/drone]
        else:
            values = samples[name]
            if sys.byteorder != "little":
                values = values[:]  # Preserve the input array
                values.byteswap()  # Convert to little-endian
            stream.write(memoryview(values).cast("B"))  # [Samples:count*8B]
        stream.write(b"\0" * padding)  # [Padding:0-7B]


@dataclass(frozen=True)
class MATExportResult:
    destination: Path
    drone_count: int
    plan: SamplingPlan


def _export_drones(scene, *, ordered=True):
    import bpy

    collection = bpy.data.collections.get("Drones")
    drones = []
    if collection is not None and collection in scene.collection.children_recursive:
        drones = [
            obj for obj in collection.all_objects
            if obj.type == "MESH" and "drones_anim_vertex_index" in obj
        ]
    # Tagged objects remain exportable even if their attachment is removed.
    if ordered:
        drones.sort(key=lambda obj: [
            (1, int(part)) if part.isdigit() else (0, part.casefold())
            for part in re.split(r"(\d+)", obj.name)
        ])
    return drones


def _sample_drones(context, drones, plan):
    """Sample world positions and object RGB on the same evaluated frames."""
    from . import safety
    from .video_projection import active_video_effects, projected_colors

    scene = context.scene
    led = getattr(scene, "drones_anim_led", None)
    samples = {name: array("d") for name in "xyzrgb"}
    original_frame, original_subframe = scene.frame_current, scene.frame_subframe
    previous_scanning = safety._scanning
    try:
        safety._scanning = True
        for column, frame in enumerate(plan):
            integer_frame = floor(frame)
            scene.frame_set(integer_frame, subframe=frame - integer_frame)
            depsgraph = context.evaluated_depsgraph_get()
            evaluated = (drone.evaluated_get(depsgraph) for drone in drones)
            effects = active_video_effects(led, frame)
            if effects:
                frame_drones = list(evaluated)
                positions = [tuple(drone.matrix_world.translation) for drone in frame_drones]
                colors = [tuple(drone.color) for drone in frame_drones]
                samples_at_frame = zip(
                    positions, projected_colors(effects, frame, positions, colors, drones=drones)
                )
            else:
                samples_at_frame = ((drone.matrix_world.translation, drone.color) for drone in evaluated)
            for drone, (position, color) in zip(drones, samples_at_frame):
                for axis, value in zip("xyz", position):
                    samples[axis].append(value)
                for channel, value in zip("rgb", color):
                    samples[channel].append(min(1.0, max(0.0, value)) * 255.0)
            context.window_manager.progress_update(column + 1)
    finally:
        try:
            scene.frame_set(original_frame, subframe=original_subframe)
        finally:
            safety._scanning = previous_scanning
        if not previous_scanning:
            safety._update(scene, context.evaluated_depsgraph_get())
    return samples


def _write_mat_file(destination, rows, columns, samples):
    """Replace the destination only after a complete write."""
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=destination.parent, suffix=".mat.tmp", delete=False
        ) as stream:
            temporary_path = stream.name
            write_mat(stream, rows, columns, samples)
        os.replace(temporary_path, destination)
        temporary_path = None
    finally:
        if temporary_path is not None:
            Path(temporary_path).unlink(missing_ok=True)


def export_mat(context, filepath):
    """Sample exportable drones and write MAT, restoring the scene on failure."""
    import bpy

    from .video_projection import validate_video_export

    props = context.scene.drones_anim_panel
    plan = sampling_plan(
        props.start_frame, props.end_frame, props.sampling_mode, props.sampling_fps,
    )
    drones = _export_drones(context.scene)
    if not drones:
        raise ValueError("没有可导出的无人机")
    if len(drones) * plan.count * 8 + 64 >= 2**31:
        raise ValueError("矩阵过大，超出当前 MAT 格式限制")
    validate_video_export(context, plan)
    destination = Path(bpy.path.abspath(bpy.path.ensure_ext(filepath, ".mat")))
    wm = context.window_manager
    wm.progress_begin(0, plan.count)
    try:
        samples = _sample_drones(context, drones, plan)
        _write_mat_file(destination, len(drones), plan.count, samples)
    finally:
        wm.progress_end()
    return MATExportResult(destination, len(drones), plan)
