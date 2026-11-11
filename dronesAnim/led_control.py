"""Self-contained LED sidebar, operators and animated viewport markers.

Adapted from Skybrush Studio's GPL-3.0-or-later LED controls.
"""

from random import shuffle

import bpy
from bpy.app.handlers import persistent
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    IntVectorProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import Image, Object, Operator, Panel, PropertyGroup, Scene, Texture, UIList

from .led_animation import get_drones, insert_color, update_emission
from .mat_export import _export_drones
from .video_projection import (
    active_video_effects,
    clear_video_frame,
    discard_unused_video,
    ensure_video_source_fps,
    load_video,
    projected_colors,
    video_natural_end,
    video_source_fps,
)
from .uv_sampling import sample_attached_colors

_draw_handle = None
_video_preview_errors = {}
_VIDEO_PRIORITY_HINT = "列表上方灯效具有更高优先级"


def _views():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                yield area


def _redraw():
    for area in _views():
        area.tag_redraw()


def _visualization_changed(self, context):
    for area in _views():
        shading = area.spaces.active.shading
        if self.visualization == "MATERIALS":
            shading.color_type = "OBJECT"
            shading.wireframe_color_type = "OBJECT"
        elif self.visualization == "MARKERS":
            shading.color_type = "SINGLE"
            shading.wireframe_color_type = "THEME"
        area.tag_redraw()


def _emission_changed(self, context):
    update_emission(self.id_data, self.emission_strength)
    _redraw()


def _video_changed(self, _context):
    _video_preview_errors.pop(self.id_data.session_uid, None)
    _redraw()


def _video_enabled_changed(self, context):
    if self.video_enabled:
        self.id_data.drones_anim_led.visualization = "MARKERS"
    _video_changed(self, context)


def _video_end_get(effect):
    if effect.video_end_locked:
        return video_natural_end(effect)
    return effect.get("video_end", video_natural_end(effect))


def _video_end_set(effect, value):
    effect["video_end"] = value


def _video_end_lock_changed(effect, context):
    if not effect.video_end_locked:
        effect["video_end"] = video_natural_end(effect)
    _video_changed(effect, context)


def _color_property(name, default=(1.0, 1.0, 1.0)):
    return FloatVectorProperty(
        name=name,
        description=f"设置{name}",
        subtype="COLOR",
        size=3,
        min=0,
        max=1,
        default=default,
    )


class DroneAnimVideoTarget(PropertyGroup):
    drone: PointerProperty(type=Object)


class DroneAnimVideoEffect(PropertyGroup):
    name: StringProperty(name="灯效名称", default="视频灯效")
    video_enabled: BoolProperty(
        name="启用灯效",
        update=_video_enabled_changed,
    )
    video_start: IntProperty(
        name="开始帧", description="视频第一张画面对应的场景帧", default=1,
        update=_video_changed,
    )
    video_end: IntProperty(
        name="结束帧", description="视频灯效生效的最后一帧（含）",
        get=_video_end_get, set=_video_end_set, update=_video_changed,
    )
    video_end_locked: BoolProperty(
        name="锁定到视频结束帧",
        description="锁定时播放一轮。解锁后可截短或循环至指定结束帧",
        default=True,
        update=_video_end_lock_changed,
    )
    video_texture: PointerProperty(type=Texture, options={"HIDDEN"})
    video_duration: IntProperty(options={"HIDDEN"}, min=0)
    video_view_captured: BoolProperty(options={"HIDDEN"})
    video_view_matrix: FloatVectorProperty(size=16, options={"HIDDEN"})
    video_viewport_size: IntVectorProperty(size=2, options={"HIDDEN"}, min=1)
    video_targets: CollectionProperty(type=DroneAnimVideoTarget)


class DroneAnimLEDProperties(PropertyGroup):
    video_effects: CollectionProperty(type=DroneAnimVideoEffect)
    video_effect_index: IntProperty(
        default=0, min=0, options={"HIDDEN"},
        update=lambda props, context: _select_video_drones(props, context),
    )
    # Retain the previous scene properties until older files have been migrated.
    video_enabled: BoolProperty(options={"HIDDEN"})
    video_start: IntProperty(default=1, options={"HIDDEN"})
    video_texture: PointerProperty(type=Texture, options={"HIDDEN"})
    video_duration: IntProperty(options={"HIDDEN"}, min=0)
    video_view_captured: BoolProperty(options={"HIDDEN"})
    video_view_matrix: FloatVectorProperty(size=16, options={"HIDDEN"})
    video_viewport_size: IntVectorProperty(size=2, options={"HIDDEN"}, min=1)
    visualization: EnumProperty(
        name="显示方式",
        description="选择无人机灯光在三维视口中的显示方式",
        items=(
            ("NONE", "不显示标记", "关闭视口中的灯光标记"),
            ("MARKERS", "彩色标记", "使用高效的彩色点标记显示无人机灯光"),
            (
                "MATERIALS",
                "材质显示",
                "显示动画物体颜色和无人机发光材质",
            ),
        ),
        default="MATERIALS",
        update=_visualization_changed,
    )
    marker_size: IntProperty(
        name="标记大小",
        description="设置视口灯光标记的像素大小",
        min=1,
        soft_max=50,
        default=25,
    )
    primary_color: _color_property("主颜色")
    secondary_color: _color_property("副颜色", (0.0, 0.0, 0.0))
    emission_strength: FloatProperty(
        name="发光强度",
        description="设置无人机灯光材质的发光强度",
        min=0,
        soft_max=5,
        default=1,
        update=_emission_changed,
    )

    uv_image: PointerProperty(
        name="纹理图像",
        type=Image,
        description="直接采样静态 UV 纹理图像，不包含材质着色或节点坐标映射",
    )
    uv_map: StringProperty(
        name="UV 贴图",
        description="附着网格的 UV 层名称；留空时使用该网格的活动渲染 UV 贴图",
    )
    uv_scope: EnumProperty(
        name="采样范围",
        description="选择要采样纹理颜色的无人机范围",
        items=(
            (
                "ALL",
                "全部附着无人机",
                "采样当前场景中本插件管理的全部附着无人机",
            ),
            ("SELECTED", "选中的无人机", "仅采样本插件管理的选中无人机"),
        ),
        default="ALL",
    )
    uv_extension: EnumProperty(
        name="图像边界",
        description="设置超出图像范围的 UV 坐标如何取色",
        items=(
            ("REPEAT", "重复", "UV 坐标超出零到一区间时重复图像"),
            ("CLAMP", "延伸", "UV 坐标超出图像范围时使用边缘像素"),
        ),
        default="REPEAT",
    )


class DroneAnimSwapLEDColorsOperator(Operator):
    bl_idname = "drones_anim.swap_led_colors"
    bl_label = "交换主副颜色"
    bl_description = "交换灯光的主颜色和副颜色"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.drones_anim_led
        primary, secondary = tuple(props.primary_color), tuple(props.secondary_color)
        props.primary_color, props.secondary_color = secondary, primary
        return {"FINISHED"}


class DroneAnimApplyLEDColorsOperator(Operator):
    bl_idname = "drones_anim.apply_led_colors"
    bl_label = "设置选中无人机的灯光颜色"
    bl_description = "为选中无人机直接设置或渐变至主颜色、副颜色或渐变色"
    bl_options = {"REGISTER", "UNDO"}

    primary_color: _color_property("主颜色")
    secondary_color: _color_property("副颜色", (0.0, 0.0, 0.0))
    color: EnumProperty(
        name="目标颜色",
        description="选择要应用的主颜色、副颜色或渐变色",
        items=(
            ("PRIMARY", "主颜色", "使用主颜色"),
            ("SECONDARY", "副颜色", "使用副颜色"),
            ("GRADIENT", "渐变色（主到副）", "按排序从主颜色过渡到副颜色"),
        ),
        default="PRIMARY",
    )
    fade: BoolProperty(
        name="渐变至目标颜色",
        default=False,
        description="从上一个颜色关键帧平滑过渡至当前帧的目标颜色",
    )
    gradient_mode: EnumProperty(
        name="渐变排序",
        description="选择无人机分配渐变颜色时的排序方式",
        items=(
            ("DEFAULT", "默认顺序", "按无人机的默认顺序分配渐变色"),
            ("RANDOM", "随机顺序", "随机排列无人机后分配渐变色"),
            ("X", "X 轴坐标", "按无人机的世界坐标 X 值排序"),
            ("Y", "Y 轴坐标", "按无人机的世界坐标 Y 值排序"),
            ("Z", "Z 轴坐标", "按无人机的世界坐标 Z 值排序"),
            ("DISTANCE", "距三维游标的距离", "按无人机到三维游标的距离排序"),
        ),
        default="DISTANCE",
    )

    @classmethod
    def poll(cls, context):
        return (
            context.scene is not None
            and context.mode == "OBJECT"
            and any(drone.select_get() for drone in get_drones(context.scene))
        )

    def invoke(self, context, event):
        props = context.scene.drones_anim_led
        self.primary_color = props.primary_color
        self.secondary_color = props.secondary_color
        if event.type == "LEFTMOUSE":
            return self.execute(context)
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        drones = [drone for drone in get_drones(context.scene) if drone.select_get()]
        if not drones:
            self.report({"ERROR"}, "请先选择本插件管理的无人机")
            return {"CANCELLED"}
        if self.color == "GRADIENT":
            if self.gradient_mode == "RANDOM":
                shuffle(drones)
            elif self.gradient_mode != "DEFAULT":
                graph = context.evaluated_depsgraph_get()
                positions = {
                    drone: drone.evaluated_get(graph).matrix_world.translation.copy()
                    for drone in drones
                }
                if self.gradient_mode == "DISTANCE":
                    cursor = context.scene.cursor.location
                    drones.sort(
                        key=lambda drone: (positions[drone] - cursor).length_squared
                    )
                else:
                    axis = "XYZ".index(self.gradient_mode)
                    drones.sort(key=lambda drone: positions[drone][axis])
        for index, drone in enumerate(drones):
            if self.color == "PRIMARY":
                color = self.primary_color
            elif self.color == "SECONDARY":
                color = self.secondary_color
            else:
                ratio = index / (len(drones) - 1) if len(drones) > 1 else 0.5
                color = tuple(
                    a * (1 - ratio) + b * ratio
                    for a, b in zip(self.primary_color, self.secondary_color)
                )
            insert_color(
                drone,
                color,
                context.scene.frame_current,
                step=not self.fade,
                frame_start=context.scene.frame_start,
            )
        _redraw()
        return {"FINISHED"}


class DroneAnimSampleUVColorsOperator(Operator):
    bl_idname = "drones_anim.sample_uv_colors"
    bl_label = "采样 UV 颜色并插入关键帧"
    bl_description = (
        "在动画播放头所在的当前帧采样 UV 颜色，并保持至下一个颜色关键帧；"
        "UV 接缝使用第一个相邻面的坐标"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.scene is not None and context.mode == "OBJECT"

    def execute(self, context):
        scene = context.scene
        props = scene.drones_anim_led
        drones = [
            drone
            for drone in get_drones(scene)
            if props.uv_scope == "ALL" or drone.select_get()
        ]
        if not drones:
            self.report({"ERROR"}, "所选范围内没有本插件管理的无人机")
            return {"CANCELLED"}
        frame = scene.frame_current + scene.frame_subframe
        try:
            colors = sample_attached_colors(
                drones,
                props.uv_image,
                context.evaluated_depsgraph_get(),
                uv_map=props.uv_map,
                repeat=props.uv_extension == "REPEAT",
            )
            for drone, color in colors:
                insert_color(
                    drone,
                    color,
                    frame,
                    step=False,
                    frame_start=scene.frame_start,
                    hold=True,
                )
        except (ValueError, RuntimeError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        finally:
            _redraw()
        self.report(
            {"INFO"},
            f"已在第 {frame:g} 帧为 {len(colors)} 架无人机插入 UV 颜色关键帧",
        )
        return {"FINISHED"}


class DroneAnimOpenVideoOperator(Operator):
    bl_idname = "drones_anim.open_led_video"
    bl_label = "打开视频"
    bl_description = "为无人机灯光投影载入本地视频"
    bl_options = {"UNDO"}

    filepath: StringProperty(subtype="FILE_PATH", options={"SKIP_SAVE"})

    @classmethod
    def description(cls, context, _properties):
        settings = getattr(context.scene, "drones_anim_led", None)
        effect = _selected_video_effect(settings) if settings is not None else None
        texture = effect.video_texture if effect is not None else None
        if isinstance(texture, bpy.types.ImageTexture) and texture.image is not None:
            return f"选择视频\n当前文件：{bpy.path.basename(texture.image.filepath)}"
        return cls.bl_description

    def invoke(self, context, _event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        props = context.scene.drones_anim_led
        try:
            texture, duration = load_video(bpy.path.abspath(self.filepath))
        except (ValueError, RuntimeError, OSError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        effect = _selected_video_effect(props)
        if effect is None:
            effect = _add_video_effect(props, context.scene.frame_current)
        previous = effect.video_texture
        effect.video_texture = texture
        effect.video_duration = duration
        if previous is None:
            effect.name = bpy.path.basename(texture.image.filepath)
        discard_unused_video(previous)
        _video_changed(effect, context)
        return {"FINISHED"}


class DroneAnimCaptureVideoViewOperator(Operator):
    bl_idname = "drones_anim.capture_led_video_view"
    bl_label = "捕获当前视角与无人机"
    bl_description = "记录当前 3D 视角和选中的无人机。没有选中无人机时保留影响范围"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        return (
            context.area is not None
            and context.area.type == "VIEW_3D"
            and _selected_video_effect(context.scene.drones_anim_led) is not None
        )

    def execute(self, context):
        region = next((region for region in context.area.regions if region.type == "WINDOW"), None)
        view = context.region_data or context.space_data.region_3d
        if view is None or region is None or min(region.width, region.height) < 1:
            self.report({"ERROR"}, "请在有效的 3D 视口中捕获视角")
            return {"CANCELLED"}
        matrix = view.perspective_matrix.copy()
        if matrix.determinant() == 0.0:
            self.report({"ERROR"}, "请等待 3D 视口更新后重新捕获")
            return {"CANCELLED"}
        effect = _selected_video_effect(context.scene.drones_anim_led)
        effect.video_view_matrix = tuple(value for row in matrix for value in row)
        effect.video_viewport_size = (region.width, region.height)
        effect.video_view_captured = True
        selected = set(context.selected_objects or ())
        if selected:
            drones = _export_drones(context.scene, ordered=False)
            targets = [drone for drone in drones if drone in selected]
            if targets:
                effect.video_targets.clear()
                if len(targets) < len(drones):
                    for drone in targets:
                        effect.video_targets.add().drone = drone
        _video_changed(effect, context)
        return {"FINISHED"}


def _selected_video_effect(props):
    index = props.video_effect_index
    return props.video_effects[index] if index < len(props.video_effects) else None


def _select_video_drones(props, context):
    effect = _selected_video_effect(props)
    if effect is None or not effect.video_view_captured:
        return
    if context.scene != props.id_data or context.mode != "OBJECT":
        return

    drones = _export_drones(context.scene, ordered=False)
    selectable = set(context.selectable_objects or ())
    if effect.video_targets:
        selectable.intersection_update(target.drone for target in effect.video_targets)
    targets = [drone for drone in drones if drone in selectable]
    target_set = set(targets)
    selected = set(context.selected_objects or ())
    view_layer = context.view_layer
    for obj in selected - target_set:
        obj.select_set(False, view_layer=view_layer)
    for drone in target_set - selected:
        drone.select_set(True, view_layer=view_layer)
    if view_layer.objects.active not in target_set:
        view_layer.objects.active = targets[0] if targets else None


def _add_video_effect(props, frame):
    effect = props.video_effects.add()
    effect.video_start = frame
    # Only choosing a list row should restore the viewport selection.
    props["video_effect_index"] = len(props.video_effects) - 1
    return effect


def _migrate_video_effect(props):
    if props.video_effects or not (props.video_texture or props.video_duration or props.video_view_captured):
        return
    effect = _add_video_effect(props, props.video_start)
    effect.video_texture = props.video_texture
    effect.video_duration = props.video_duration
    effect.video_view_captured = props.video_view_captured
    effect.video_view_matrix = tuple(props.video_view_matrix)
    effect.video_viewport_size = tuple(props.video_viewport_size)
    effect["video_enabled"] = props.video_enabled
    if isinstance(effect.video_texture, bpy.types.ImageTexture) and effect.video_texture.image:
        effect.name = effect.video_texture.image.name
    props.video_texture = None
    props.video_duration = 0
    props.video_view_captured = False
    props.video_enabled = False


def _migrate_loaded_video_effects():
    for scene in bpy.data.scenes:
        props = scene.drones_anim_led
        _migrate_video_effect(props)
        for effect in props.video_effects:
            if "video_end" in effect and "video_end_locked" not in effect:
                # Older ranges beyond the source duration used to stop after one pass.
                old_natural_end = effect.video_start + max(0, effect.video_duration - 1)
                effect["video_end_locked"] = effect["video_end"] >= old_natural_end
            if effect.video_texture is not None:
                try:
                    ensure_video_source_fps(effect.video_texture)
                except (OSError, RuntimeError, ValueError):
                    # The user can reselect missing or unsupported media from the panel.
                    pass


class DroneAnimEditVideoEffectsOperator(Operator):
    bl_idname = "drones_anim.edit_video_effects"
    bl_label = "编辑视频灯效列表"
    bl_options = {"UNDO"}

    action: EnumProperty(items=(
        ("ADD", "添加", ""),
        ("REMOVE", "移除", ""),
        ("UP", "上移", ""),
        ("DOWN", "下移", ""),
    ))

    @classmethod
    def description(cls, context, properties):
        if properties.action == "UP":
            return f"上移灯效。{_VIDEO_PRIORITY_HINT}"
        if properties.action == "DOWN":
            return f"下移灯效。{_VIDEO_PRIORITY_HINT}"
        return cls.bl_label

    def execute(self, context):
        props = context.scene.drones_anim_led
        effects = props.video_effects
        index = props.video_effect_index
        if self.action == "ADD":
            _add_video_effect(props, context.scene.frame_current)
        elif index >= len(effects):
            return {"CANCELLED"}
        elif self.action == "REMOVE":
            texture = effects[index].video_texture
            effects.remove(index)
            props["video_effect_index"] = min(index, max(0, len(effects) - 1))
            discard_unused_video(texture)
        else:
            target = index + (-1 if self.action == "UP" else 1)
            if not 0 <= target < len(effects):
                return {"CANCELLED"}
            effects.move(index, target)
            props["video_effect_index"] = target
            self.report({"INFO"}, _VIDEO_PRIORITY_HINT)
        _video_changed(props, context)
        return {"FINISHED"}


class DRONES_ANIM_UL_video_effects(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index=0):
        row = layout.row(align=True)
        ready = item.video_texture is not None and item.video_view_captured
        toggle = row.row(align=True)
        toggle.enabled = item.video_enabled or ready
        toggle.prop(item, "video_enabled", text="")
        row.prop(item, "name", text="", emboss=False, icon="FILE_MOVIE")
        if item.video_duration:
            row.label(text=f"{item.video_start}–{item.video_end}")


def _draw_video_effects(layout, props):
    box = layout.box()
    box.label(text="视频灯效", icon="FILE_MOVIE")
    row = box.row()
    row.template_list(
        "DRONES_ANIM_UL_video_effects", "", props, "video_effects",
        props, "video_effect_index", rows=3, sort_lock=True,
    )
    buttons = row.column(align=True)
    operator = DroneAnimEditVideoEffectsOperator.bl_idname
    buttons.operator(operator, text="", icon="ADD").action = "ADD"
    effect = _selected_video_effect(props)
    if effect is None:
        return
    buttons.operator(operator, text="", icon="REMOVE").action = "REMOVE"
    if len(props.video_effects) > 1:
        buttons.separator()
        buttons.operator(operator, text="", icon="TRIA_UP").action = "UP"
        buttons.operator(operator, text="", icon="TRIA_DOWN").action = "DOWN"
    texture = effect.video_texture
    image = texture.image if isinstance(texture, bpy.types.ImageTexture) else None
    box.operator(
        DroneAnimOpenVideoOperator.bl_idname,
        text=bpy.path.basename(image.filepath) if image is not None else "请选择视频",
        icon="FILE_FOLDER",
    )
    if image is not None:
        box.label(text=f"总帧数：{effect.video_duration}")
        fps = video_source_fps(texture)
        if fps > 0:
            box.label(text=f"素材帧率：{fps:.3f}".rstrip("0").rstrip(".") + " FPS")
        else:
            box.label(text="素材帧率未知，请重新选择视频", icon="ERROR")
    box.prop(effect, "video_start")
    end_row = box.row(align=True)
    end_field = end_row.row(align=True)
    end_field.enabled = not effect.video_end_locked
    end_field.prop(effect, "video_end")
    end_row.prop(
        effect, "video_end_locked", text="", toggle=True,
        icon="LOCKED" if effect.video_end_locked else "UNLOCKED",
    )
    if effect.video_end < effect.video_start:
        box.label(text="结束帧需大于或等于开始帧", icon="ERROR")
    elif effect.video_duration and effect.video_end > video_natural_end(effect):
        box.label(text=f"第 {video_natural_end(effect) + 1} 帧起循环播放")
    box.operator(DroneAnimCaptureVideoViewOperator.bl_idname, icon="VIEW_CAMERA")
    error = _video_preview_errors.get(props.id_data.session_uid)
    if error:
        box.label(text=error, icon="ERROR")


class DroneAnimLEDControlPanel(Panel):
    bl_idname = "OBJECT_PT_drones_anim_led_control"
    bl_label = "灯光控制"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "灯光控制"

    def draw(self, context):
        props = context.scene.drones_anim_led
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        shading = context.space_data.shading
        expected = {"MATERIALS": ("OBJECT", "OBJECT"), "MARKERS": ("THEME", "SINGLE")}
        wire, solid = expected.get(props.visualization, (None, None))
        if (
            shading.type == "WIREFRAME"
            and wire
            and shading.wireframe_color_type != wire
        ):
            color_name = {"OBJECT": "物体", "THEME": "主题"}[wire]
            layout.label(text=f"请将线框颜色设为「{color_name}」", icon="ERROR")
        elif shading.type == "SOLID" and solid and shading.color_type != solid:
            color_name = {"OBJECT": "物体", "SINGLE": "单一"}[solid]
            layout.label(text=f"请将实体视图颜色设为「{color_name}」", icon="ERROR")
        layout.prop(props, "visualization")
        if props.visualization == "MARKERS":
            layout.prop(props, "marker_size")
        row = layout.row()
        row.use_property_split = False
        row.prop(props, "primary_color", text="主颜色", icon="COLOR")
        row.operator(
            DroneAnimSwapLEDColorsOperator.bl_idname, text="", icon="ARROW_LEFTRIGHT"
        )
        row.prop(props, "secondary_color", text="副颜色", icon="COLOR")
        for fade, label in ((False, "应用"), (True, "渐变至")):
            row = layout.row()
            for color in ("PRIMARY", "SECONDARY"):
                operator = row.operator(
                    DroneAnimApplyLEDColorsOperator.bl_idname, text=label
                )
                operator.color, operator.fade = color, fade
                operator.primary_color = props.primary_color
                operator.secondary_color = props.secondary_color

        box = layout.box()
        box.label(text="UV 纹理采样", icon="TEXTURE")
        box.template_ID(props, "uv_image", open="image.open")
        box.prop(props, "uv_map")
        frame = context.scene.frame_current + context.scene.frame_subframe
        box.label(text=f"当前帧：{frame:g}", icon="TIME")
        box.prop(props, "uv_scope")
        box.prop(props, "uv_extension")
        box.label(text="UV 贴图留空：使用活动渲染 UV")
        box.label(text="UV 接缝：使用第一个相邻面")
        box.operator(DroneAnimSampleUVColorsOperator.bl_idname, icon="KEY_HLT")


        _draw_video_effects(layout, props)


def _marker_data(scene, graph):
    props = scene.drones_anim_led
    frame = scene.frame_current + scene.frame_subframe
    effects = active_video_effects(props, frame)
    drones = _export_drones(scene, ordered=False) if effects else get_drones(scene)
    if not effects:
        drones = [drone for drone in drones if drone.visible_get()]
    evaluated = [drone.evaluated_get(graph) for drone in drones]
    positions = [tuple(drone.matrix_world.translation) for drone in evaluated]
    colors = [tuple(drone.color) for drone in evaluated]
    if effects and drones:
        try:
            colors = projected_colors(effects, frame, positions, colors, drones=drones)
        except (ValueError, RuntimeError, OSError) as error:
            _video_preview_errors[scene.session_uid] = str(error)
        else:
            _video_preview_errors.pop(scene.session_uid, None)
        visible = [index for index, drone in enumerate(drones) if drone.visible_get()]
        positions = [positions[index] for index in visible]
        colors = [tuple(colors[index]) for index in visible]
    return positions, colors


def _draw_markers():
    import gpu
    from gpu_extras.batch import batch_for_shader

    context = bpy.context
    scene = context.scene
    if scene is None or context.region_data is None:
        return
    props = scene.drones_anim_led
    if props.visualization != "MARKERS" or not context.space_data.overlay.show_overlays:
        return
    graph = context.evaluated_depsgraph_get()
    positions, colors = _marker_data(scene, graph)
    if not positions:
        return
    shader = gpu.shader.from_builtin("POINT_FLAT_COLOR")
    batch = batch_for_shader(
        shader,
        "POINTS",
        {"pos": positions, "color": colors},
    )
    blend, depth = gpu.state.blend_get(), gpu.state.depth_test_get()
    try:
        gpu.state.blend_set("ALPHA")
        gpu.state.depth_test_set("LESS_EQUAL")
        gpu.state.point_size_set(props.marker_size)
        shader.bind()
        batch.draw(shader)
    finally:
        gpu.state.point_size_set(1)
        gpu.state.depth_test_set(depth)
        gpu.state.blend_set(blend)


@persistent
def _on_frame(scene, depsgraph=None):
    _redraw()


@persistent
def _on_load(_unused):
    clear_video_frame()
    _video_preview_errors.clear()
    _migrate_loaded_video_effects()
    for scene in bpy.data.scenes:
        props = scene.drones_anim_led
        update_emission(scene, props.emission_strength)
    _visualization_changed(bpy.context.scene.drones_anim_led, bpy.context)


def register():
    global _draw_handle
    Scene.drones_anim_led = PointerProperty(type=DroneAnimLEDProperties)
    if not bpy.app.timers.is_registered(_migrate_loaded_video_effects):
        bpy.app.timers.register(_migrate_loaded_video_effects, first_interval=0.0)
    if _on_frame not in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.append(_on_frame)
    if _on_load not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_on_load)
    if _draw_handle is None:
        _draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            _draw_markers, (), "WINDOW", "POST_VIEW"
        )


def unregister():
    global _draw_handle
    if bpy.app.timers.is_registered(_migrate_loaded_video_effects):
        bpy.app.timers.unregister(_migrate_loaded_video_effects)
    clear_video_frame()
    _video_preview_errors.clear()
    if _on_frame in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.remove(_on_frame)
    if _on_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_on_load)
    if _draw_handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, "WINDOW")
        _draw_handle = None
    if hasattr(Scene, "drones_anim_led"):
        del Scene.drones_anim_led
