"""Self-contained safety panel, frame handlers and viewport warnings."""

from collections import Counter
from dataclasses import dataclass, field

import bpy
from bpy.app.handlers import persistent
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import Operator, Panel, PropertyGroup, Scene

from .safety_math import Limits, Result, Snapshot, evaluate_frame, warning_messages


@dataclass
class _SceneState:
    snapshots: list[Snapshot] = field(default_factory=list)
    result: Result | None = None


_states: dict[int, _SceneState] = {}
_scanning = False
_draw_handle = None
_PLAYBACK_CHECK_INTERVAL = 5
_WARNING_COLORS = {
    "proximity": (1.0, 0.15, 0.15, 0.9),
    "altitude": (1.0, 0.45, 0.1, 0.9),
    "velocity": (1.0, 0.85, 0.1, 0.9),
    "acceleration": (0.8, 0.3, 1.0, 0.9),
    "yaw": (0.2, 0.8, 1.0, 0.9),
}
_VALIDATION_CATEGORIES = {
    "距离": "proximity",
    "高度": "altitude",
    "速度": "velocity",
    "加速度": "acceleration",
    "偏航角速度": "yaw",
}


def _get_drones(scene):
    collection = bpy.data.collections.get("Drones")
    if collection is None or collection not in scene.collection.children_recursive:
        return ()
    return tuple(obj for obj in collection.objects if obj.type == "MESH")


def _snapshot(scene, depsgraph):
    positions = {}
    yaws = {}
    for drone in _get_drones(scene):
        evaluated = drone.evaluated_get(depsgraph)
        matrix = evaluated.matrix_world
        positions[drone.name] = tuple(matrix.translation)
        yaws[drone.name] = matrix.to_euler("XYZ").z
    return Snapshot(scene.frame_current, positions, yaws)


def _limits(props):
    return Limits(
        proximity=props.proximity_warning_threshold,
        proximity_target=props.proximity_warning_target,
        min_navigation_altitude=props.min_navigation_altitude,
        max_altitude=props.altitude_warning_threshold,
        max_velocity_xy=props.velocity_xy_warning_threshold,
        max_velocity_z_down=props.velocity_z_warning_threshold,
        max_velocity_z_up=(
            props.velocity_z_warning_threshold_up
            if props.velocity_z_warning_different_up
            else props.velocity_z_warning_threshold
        ),
        max_acceleration=props.acceleration_warning_threshold,
        max_yaw_rate=props.yaw_rate_warning_threshold,
        proximity_enabled=props.proximity_warning_enabled,
        altitude_enabled=props.altitude_warning_enabled,
        velocity_enabled=props.velocity_warning_enabled,
        acceleration_enabled=props.acceleration_warning_enabled,
        yaw_rate_enabled=props.yaw_rate_warning_enabled,
    )


def _redraw():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


def _is_playing(scene):
    return any(
        window.scene == scene and window.screen.is_animation_playing
        for window in bpy.context.window_manager.windows
    )


def _update(scene, depsgraph, *, force=False):
    if _scanning or not hasattr(scene, "drones_anim_safety"):
        return
    state = _states.setdefault(scene.as_pointer(), _SceneState())
    props = scene.drones_anim_safety
    if not props.enabled:
        state.result = None
        state.snapshots.clear()
        _redraw()
        return
    snapshot = _snapshot(scene, depsgraph)
    history = state.snapshots
    if history and snapshot.frame == history[-1].frame:
        history[-1] = snapshot
    else:
        if history and snapshot.frame != history[-1].frame + 1:
            history.clear()
        history.append(snapshot)
        del history[:-3]
    if (
        not force
        and _is_playing(scene)
        and state.result is not None
        and abs(snapshot.frame - state.result.frame) < _PLAYBACK_CHECK_INTERVAL
    ):
        _redraw()
        return
    fps = scene.render.fps / scene.render.fps_base
    state.result = evaluate_frame(
        snapshot,
        _limits(props),
        fps,
        previous=history[-2] if len(history) > 1 else None,
        earlier=history[-3] if len(history) > 2 else None,
    )
    _redraw()


@persistent
def _on_scene_update(scene, depsgraph):
    _update(scene, depsgraph)


@persistent
def _on_playback_stopped(scene, depsgraph):
    _update(scene, depsgraph, force=True)


@persistent
def _on_load(_unused):
    _states.clear()
    _redraw()


def _settings_changed(self, context):
    if context is not None and context.scene is not None:
        _update(context.scene, context.evaluated_depsgraph_get(), force=True)


def _display_changed(self, context):
    # Display toggles must not evaluate the scene from an RNA update callback.
    _redraw()


class DroneAnimSafetyProperties(PropertyGroup):
    enabled: BoolProperty(
        name="启用安全检查", default=True, update=_settings_changed
    )
    marker_size: IntProperty(
        name="标记大小", default=25, min=1, soft_max=50, update=_settings_changed
    )
    proximity_warning_enabled: BoolProperty(
        name="距离警告", default=True, update=_settings_changed
    )
    proximity_warning_threshold: FloatProperty(
        name="最小距离", default=3.0, min=0, soft_max=10,
        unit="LENGTH", update=_settings_changed
    )
    proximity_warning_target: EnumProperty(
        name="检测范围",
        items=(
            ("ALL", "所有无人机", "检测所有无人机"),
            ("ABOVE_MIN_NAV_ALT", "最低导航高度以上", "仅检测最低导航高度以上的无人机"),
        ),
        default="ABOVE_MIN_NAV_ALT", update=_settings_changed,
    )
    show_proximity_pair_lines: BoolProperty(
        name="显示距离警告无人机对连线",
        description="用红色连线显示所有间距小于最小距离的无人机对",
        default=False, update=_display_changed,
    )
    altitude_warning_enabled: BoolProperty(
        name="高度警告", default=True, update=_settings_changed
    )
    min_navigation_altitude: FloatProperty(
        name="最低导航高度", default=2.5, min=0, unit="LENGTH",
        update=_settings_changed,
    )
    altitude_warning_threshold: FloatProperty(
        name="最高高度", default=150, min=0, unit="LENGTH",
        update=_settings_changed,
    )
    velocity_warning_enabled: BoolProperty(
        name="速度警告", default=True, update=_settings_changed
    )
    velocity_xy_warning_threshold: FloatProperty(
        name="水平速度上限", default=10, min=0, unit="VELOCITY",
        update=_settings_changed,
    )
    velocity_z_warning_threshold: FloatProperty(
        name="垂直速度下限", default=2, min=0, unit="VELOCITY",
        update=_settings_changed,
    )
    velocity_z_warning_different_up: BoolProperty(
        name="区分上升速度", default=False, update=_settings_changed
    )
    velocity_z_warning_threshold_up: FloatProperty(
        name="上升速度上限", default=2, min=0, unit="VELOCITY",
        update=_settings_changed,
    )
    acceleration_warning_enabled: BoolProperty(
        name="加速度警告", default=True, update=_settings_changed
    )
    acceleration_warning_threshold: FloatProperty(
        name="加速度上限", default=4, min=0, unit="ACCELERATION",
        update=_settings_changed,
    )
    yaw_rate_warning_enabled: BoolProperty(
        name="偏航角速度警告", default=True, update=_settings_changed
    )
    yaw_rate_warning_threshold: FloatProperty(
        name="偏航角速度上限 (度/秒)", default=30, min=0,
        update=_settings_changed,
    )
    validation_summary: StringProperty(name="区间检查结果", default="")


class DroneAnimValidateTrajectoriesOperator(Operator):
    bl_idname = "drones_anim.validate_trajectories"
    bl_label = "检查整个动画"
    bl_description = "逐帧检查当前场景的动画范围，并汇总触发安全警告的帧数"

    @classmethod
    def poll(cls, context):
        return context.scene is not None and bool(_get_drones(context.scene))

    def execute(self, context):
        global _scanning
        scene = context.scene
        props = scene.drones_anim_safety
        start, end = scene.frame_start, scene.frame_end
        if end < start:
            self.report({"ERROR"}, "场景帧范围无效")
            return {"CANCELLED"}
        frame, subframe = scene.frame_current, scene.frame_subframe
        limits = _limits(props)
        counts = Counter()
        first_frame = {}
        earlier = previous = None
        fps = scene.render.fps / scene.render.fps_base
        _scanning = True
        try:
            for index in range(start, end + 1):
                scene.frame_set(index)
                current = _snapshot(scene, context.evaluated_depsgraph_get())
                if not current.positions:
                    props.validation_summary = "未找到无人机"
                    self.report({"WARNING"}, props.validation_summary)
                    return {"CANCELLED"}
                result = evaluate_frame(current, limits, fps, previous, earlier)
                for category, names in result.warnings.items():
                    if names:
                        counts[category] += 1
                        first_frame.setdefault(category, index)
                earlier, previous = previous, current
        finally:
            scene.frame_set(frame, subframe=subframe)
            _scanning = False
            _states.pop(scene.as_pointer(), None)
            _update(scene, context.evaluated_depsgraph_get())

        labels = {
            "proximity": "距离", "altitude": "高度", "velocity": "速度",
            "acceleration": "加速度", "yaw": "偏航角速度",
        }
        props.validation_summary = (
            "；".join(
                f"{label}: {counts[category]} 帧 (首帧 {first_frame[category]})"
                for category, label in labels.items()
                if counts[category]
            )
            or "检查通过：未发现警告"
        )
        self.report(
            {"WARNING"} if counts else {"INFO"},
            f"已检查 {end - start + 1} 帧。{props.validation_summary}",
        )
        _redraw()
        return {"FINISHED"}


class DroneAnimSafetyPanel(Panel):
    bl_idname = "OBJECT_PT_drones_anim_safety"
    bl_label = "安全检查"
    bl_parent_id = "OBJECT_PT_drones_anim_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "无人机动画"

    def draw_header(self, context):
        self.layout.prop(context.scene.drones_anim_safety, "enabled", text="")

    def draw(self, context):
        props = context.scene.drones_anim_safety
        layout = self.layout
        col = layout.column()
        col.enabled = props.enabled
        col.prop(props, "marker_size")

        col.prop(props, "proximity_warning_enabled")
        row = col.row()
        row.enabled = props.proximity_warning_enabled
        row.prop(props, "proximity_warning_threshold", text="最小距离")
        row = col.row()
        row.enabled = props.proximity_warning_enabled
        row.prop(props, "proximity_warning_target")
        row = col.row()
        row.enabled = props.proximity_warning_enabled
        row.prop(props, "show_proximity_pair_lines", toggle=True)

        col.prop(props, "altitude_warning_enabled")
        row = col.row()
        row.enabled = props.altitude_warning_enabled
        row.prop(props, "min_navigation_altitude", text="最低")
        row.prop(props, "altitude_warning_threshold", text="最高")

        col.prop(props, "velocity_warning_enabled")
        row = col.row()
        row.enabled = props.velocity_warning_enabled
        row.prop(props, "velocity_xy_warning_threshold", text="水平")
        row = col.row()
        row.enabled = props.velocity_warning_enabled
        row.prop(props, "velocity_z_warning_threshold", text="下降")
        row.prop(props, "velocity_z_warning_different_up", text="区分上升")
        row = col.row()
        row.enabled = props.velocity_warning_enabled and props.velocity_z_warning_different_up
        row.prop(props, "velocity_z_warning_threshold_up", text="上升")

        col.prop(props, "acceleration_warning_enabled")
        row = col.row()
        row.enabled = props.acceleration_warning_enabled
        row.prop(props, "acceleration_warning_threshold")
        col.prop(props, "yaw_rate_warning_enabled")
        row = col.row()
        row.enabled = props.yaw_rate_warning_enabled
        row.prop(props, "yaw_rate_warning_threshold")

        layout.separator()
        layout.operator(DroneAnimValidateTrajectoriesOperator.bl_idname)


def _draw_warnings():
    import blf
    import gpu
    from bpy_extras.view3d_utils import location_3d_to_region_2d
    from gpu_extras.batch import batch_for_shader
    from mathutils import Vector

    context = bpy.context
    scene = context.scene
    if scene is None or context.region_data is None or not hasattr(scene, "drones_anim_safety"):
        return
    props = scene.drones_anim_safety
    if not props.enabled:
        return
    state = _states.get(scene.as_pointer())
    result = state.result if state else None
    messages = warning_messages(result, _limits(props)) if result else []
    if props.validation_summary:
        messages.append((None, "区间检查:"))
        for item in props.validation_summary.split("；"):
            category = _VALIDATION_CATEGORIES.get(item.partition(":")[0])
            messages.append((category, item))
    if not messages:
        return
    if result and result.warning_count and state.snapshots:
        positions = state.snapshots[-1].positions
        size = props.marker_size
        categories_by_drone = {}
        for category, names in result.warnings.items():
            for name in names:
                categories_by_drone.setdefault(name, []).append(category)
        shader = gpu.shader.from_builtin("UNIFORM_COLOR")
        gpu.state.blend_set("ALPHA")
        try:
            if (
                props.proximity_warning_enabled
                and props.show_proximity_pair_lines
                and result.close_pairs
            ):
                vertices = []
                for pair in result.close_pairs:
                    endpoints = []
                    for name in pair:
                        point = positions.get(name)
                        if point is None:
                            break
                        screen = location_3d_to_region_2d(
                            context.region, context.region_data, Vector(point)
                        )
                        if screen is None:
                            break
                        endpoints.append(tuple(screen))
                    if len(endpoints) == 2:
                        vertices.extend(endpoints)
                if vertices:
                    shader.bind()
                    shader.uniform_float("color", _WARNING_COLORS["proximity"])
                    batch_for_shader(shader, "LINES", {"pos": vertices}).draw(shader)

            for category, names in result.warnings.items():
                vertices = []
                for name in names:
                    point = positions.get(name)
                    if point is None:
                        continue
                    screen = location_3d_to_region_2d(
                        context.region, context.region_data, Vector(point)
                    )
                    if screen is None:
                        continue
                    x, y = screen
                    # Nested squares keep every category visible on shared drones.
                    marker_index = categories_by_drone[name].index(category)
                    radius = max(
                        1,
                        size / 2
                        * (1 - marker_index / (len(categories_by_drone[name]) + 1)),
                    )
                    corners = ((x - radius, y - radius), (x + radius, y - radius),
                               (x + radius, y + radius), (x - radius, y + radius))
                    vertices.extend((corners[0], corners[1], corners[2],
                                     corners[0], corners[2], corners[3]))
                if vertices:
                    shader.bind()
                    shader.uniform_float("color", _WARNING_COLORS[category])
                    batch_for_shader(shader, "TRIS", {"pos": vertices}).draw(shader)
        finally:
            gpu.state.blend_set("NONE")

    scale = context.preferences.system.ui_scale
    toolbar = next(
        (
            region
            for region in context.area.regions
            if region.type == "TOOLS" and region.width > 1
        ),
        None,
    )
    text_x = (toolbar.width if toolbar else 0) + 14 * scale
    stats_height = 120 * scale if context.space_data.overlay.show_stats else 0
    viewport_label_height = 56 * scale if context.space_data.overlay.show_text else 0
    text_y = context.region.height - 64 * scale - viewport_label_height - stats_height
    line_height = 22 * scale
    blf.size(0, round(10 * scale))
    for index, (category, message) in enumerate(messages):
        blf.color(0, *_WARNING_COLORS.get(category, (1.0, 1.0, 1.0, 1.0)))
        blf.position(0, text_x, text_y - index * line_height, 0)
        blf.draw(0, message)


def register():
    global _draw_handle
    Scene.drones_anim_safety = PointerProperty(type=DroneAnimSafetyProperties)
    for handler in (bpy.app.handlers.frame_change_post, bpy.app.handlers.depsgraph_update_post):
        if _on_scene_update not in handler:
            handler.append(_on_scene_update)
    if _on_playback_stopped not in bpy.app.handlers.animation_playback_post:
        bpy.app.handlers.animation_playback_post.append(_on_playback_stopped)
    if _on_load not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_on_load)
    if _draw_handle is None:
        _draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            _draw_warnings, (), "WINDOW", "POST_PIXEL"
        )


def unregister():
    global _draw_handle
    for handler in (bpy.app.handlers.frame_change_post, bpy.app.handlers.depsgraph_update_post):
        if _on_scene_update in handler:
            handler.remove(_on_scene_update)
    if _on_playback_stopped in bpy.app.handlers.animation_playback_post:
        bpy.app.handlers.animation_playback_post.remove(_on_playback_stopped)
    if _on_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_on_load)
    if _draw_handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, "WINDOW")
        _draw_handle = None
    _states.clear()
    if hasattr(Scene, "drones_anim_safety"):
        del Scene.drones_anim_safety
