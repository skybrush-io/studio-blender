"""Motion-analysis controls, synchronous calculation and optional background jobs."""

import re
from pathlib import Path
from time import perf_counter, sleep

import bpy
from bpy.app.handlers import persistent
from bpy.props import BoolProperty, EnumProperty, IntProperty, PointerProperty, StringProperty
from bpy.types import Operator, Panel, PropertyGroup, Scene
from bpy_extras.io_utils import ExportHelper

from .job import AnalysisJob
from .sampling import calculate_motion
from . import plot

_results = {}
_views = set()
_view_ops = {}
_jobs = {}
_draw_handle = None


def _redraw():
    """Request a redraw of all 3D views."""
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


def _settings_changed(self, context):
    """Refresh charts when display settings change."""
    _redraw()


def _has_drones(scene):
    """Check button availability without collecting or sorting every drone."""
    collection = bpy.data.collections.get("Drones")
    return (
        collection is not None
        and collection in scene.collection.children_recursive
        and any(obj.type == "MESH" for obj in collection.all_objects)
    )


def _drones(scene):
    """Collect scene drones in natural name order."""
    collection = bpy.data.collections.get("Drones")
    if collection is None or collection not in scene.collection.children_recursive:
        return []
    # All objects in a scene-linked collection already belong to that scene.
    objects = [obj for obj in collection.all_objects
               if obj.type == "MESH"]
    objects.sort(key=lambda obj: [(1, int(part)) if part.isdigit() else (0, part.casefold())
                                  for part in re.split(r"(\d+)", obj.name)])
    return objects


class DroneMotionAnalysisProperties(PropertyGroup):
    background: BoolProperty(
        name="后台计算",
        description="勾选后计算期间可继续操作，支持Esc取消；关闭时同步计算，完成后显示图表",
        default=False,
    )
    style: EnumProperty(
        name="曲线显示",
        items=(("ENVELOPE", "包络线", "每个采样点的全机最小值与最大值"),
               ("CURVES", "全部曲线", "显示每架无人机的曲线"),
               ("BOTH", "曲线与包络", "叠加显示全部曲线与包络线")),
        default="ENVELOPE", update=_settings_changed,
    )
    time_axis: EnumProperty(
        name="横轴",
        items=(("FRAMES", "帧", "显示场景帧号"),
               ("SECONDS", "秒", "显示从起始帧经过的秒数")),
        default="SECONDS", update=_settings_changed,
    )


class DroneMotionCalculateOperator(Operator):
    bl_idname = "drones_anim.calculate_motion_analysis"
    bl_label = "计算全局运动曲线"
    bl_description = "计算八项运动曲线并自动打开独立图表窗口；后台计算支持Esc取消"
    _timer = None
    _job = None
    _wm = None
    _key = None
    _next_tick = 0.0
    _progress = 0.0

    @classmethod
    def poll(cls, context):
        """Allow calculation when drones exist and no job is running."""
        return context.scene is not None and not _jobs and _has_drones(context.scene)

    def _start(self, context):
        """Save a scene snapshot and launch the worker."""
        self._key = context.scene.as_pointer()
        self._wm = context.window_manager
        self._next_tick = 0.0
        self._progress = 0.0
        self._job = AnalysisJob(context.scene, context.view_layer,
                                [obj.name for obj in _drones(context.scene)])
        _jobs[self._key] = self
        _redraw()

    def _cleanup(self):
        """Close the job, remove its timer and reset progress."""
        job, timer = self._job, self._timer
        self._job = self._timer = None
        try:
            if job is not None:
                job.close()
        finally:
            try:
                if timer is not None:
                    self._wm.event_timer_remove(timer)
            finally:
                if _jobs.get(self._key) is self:
                    _jobs.pop(self._key, None)
                self._progress = 0.0
                _redraw()

    def _poll_result(self):
        """Update progress and return a terminal status when ready."""
        try:
            progress, data = self._job.poll()
            if progress != self._progress:
                self._progress = progress
                _redraw()
            if data is None:
                return None
            self._cleanup()
            return self._store_result(data)
        except Exception as exc:
            self._cleanup()
            self.report({"ERROR"}, f"运动分析失败: {exc}")
            return {"CANCELLED"}

    def _store_result(self, data):
        """Publish a completed result and invalidate cached chart geometry."""
        _results[self._key] = data
        plot.clear_cache()
        self.report({"INFO"}, f"已计算 {len(data.names)} 架无人机、{data.end - data.start + 1} 帧的8项曲线")
        return {"FINISHED"}

    def _execute_sync(self, context):
        """Calculate in the main thread and preserve old results on failure."""
        self._key = context.scene.as_pointer()
        self._wm = context.window_manager
        _jobs[self._key] = self
        try:
            try:
                data = calculate_motion(context.scene, context.view_layer, _drones(context.scene))
            finally:
                self._cleanup()
            return self._store_result(data)
        except Exception as exc:
            self.report({"ERROR"}, f"运动分析失败: {exc}")
            return {"CANCELLED"}

    def execute(self, context):
        """Calculate directly, or wait for the optional background worker."""
        if not context.scene.drones_anim_analysis.background:
            return self._execute_sync(context)
        try:
            self._start(context)
            while True:
                status = self._poll_result()
                if status is not None:
                    return status
                sleep(0.05)
        except Exception as exc:
            self._cleanup()
            self.report({"ERROR"}, f"运动分析启动失败: {exc}")
            return {"CANCELLED"}

    def invoke(self, context, event):
        """Run the selected mode and open charts after successful calculation."""
        self._window, self._area = context.window, context.area
        if not context.scene.drones_anim_analysis.background:
            status = self._execute_sync(context)
            if status == {"FINISHED"}:
                self._show_result(context)
            return status
        try:
            self._start(context)
            self._timer = context.window_manager.event_timer_add(0.1, window=context.window)
            context.window_manager.modal_handler_add(self)
        except Exception as exc:
            self._cleanup()
            self.report({"ERROR"}, f"运动分析启动失败: {exc}")
            return {"CANCELLED"}
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        """Poll on timer events and cancel on Esc."""
        if self._job is None:
            return {"CANCELLED"}
        if event.type == "ESC":
            self._cleanup()
            self.report({"INFO"}, "已取消运动分析")
            return {"CANCELLED"}
        if event.type == "TIMER":
            now = perf_counter()
            # Timer events only poll the worker; they never evaluate the scene.
            if now < self._next_tick:
                return {"RUNNING_MODAL"}
            self._next_tick = now + 0.1
            status = self._poll_result()
            if status is not None:
                if status == {"FINISHED"}:
                    self._show_result(context)
                return status
        return {"PASS_THROUGH"}

    def _show_result(self, context):
        """Schedule the chart window after the calculation operator exits."""
        window, area, key = self._window, self._area, self._key
        data = _results.get(key)

        def open_window():
            """Open the chart window if the cached result is still current."""
            if _results.get(key) is not data:
                return None
            try:
                region = next(r for r in area.regions if r.type == "WINDOW")
                with bpy.context.temp_override(window=window, area=area, region=region):
                    bpy.ops.drones_anim.open_motion_window()
            except Exception as exc:
                print(f"Drone motion: 计算已完成，图表窗口未能自动打开: {exc}")
            return None

        # Finish the calculation operator before duplicating its source area/window.
        bpy.app.timers.register(open_window, first_interval=0.0)

    def cancel(self, context):
        """Release resources when Blender cancels the operator."""
        self._cleanup()


class DroneMotionViewOperator(Operator):
    bl_idname = "drones_anim.view_motion_analysis"
    bl_label = "显示 / 关闭8项图表"
    bl_description = "在当前3D视图显示图表；点击曲线跳转对应帧，Esc关闭"

    @classmethod
    def poll(cls, context):
        """Require a 3D view and a cached analysis result."""
        return (context.area is not None and context.area.type == "VIEW_3D"
                and context.scene.as_pointer() in _results)

    def invoke(self, context, event):
        """Toggle charts in the current 3D view."""
        self._area = context.area
        self._window = context.window
        self._key = context.area.as_pointer()
        if self._key in _views:
            _view_ops[self._key]._close()
            return {"FINISHED"}
        self._space = context.space_data
        self._original_ui = self._space.show_region_ui
        self._original_toolbar = self._space.show_region_toolbar
        self._original_overlays = self._space.overlay.show_overlays
        self._original_gizmo = self._space.show_gizmo
        self._space.show_region_ui = False
        self._space.show_region_toolbar = False
        self._space.overlay.show_overlays = False
        self._space.show_gizmo = False
        _ensure_draw_handler()
        _views.add(self._key)
        _view_ops[self._key] = self
        context.window_manager.modal_handler_add(self)
        _redraw()
        return {"RUNNING_MODAL"}

    def _close(self):
        """Close charts and restore the original view settings."""
        if _view_ops.get(self._key) is not self:
            return
        _views.discard(self._key)
        _view_ops.pop(self._key, None)
        try:
            self._space.show_region_ui = self._original_ui
            self._space.show_region_toolbar = self._original_toolbar
            self._space.overlay.show_overlays = self._original_overlays
            self._space.show_gizmo = self._original_gizmo
        except ReferenceError:
            pass
        _redraw()

    def modal(self, context, event):
        """Handle chart clicks and Esc; pass other events through."""
        if _view_ops.get(self._key) is not self:
            return {"CANCELLED"}
        try:
            region = next((r for r in self._area.regions if r.type == "WINDOW"), None)
            if self._area.type != "VIEW_3D":
                region = None
        except ReferenceError:
            region = None
        if region is None or self._key not in _views:
            self._close()
            return {"CANCELLED"}
        if event.type == "ESC":
            self._close()
            return {"CANCELLED"}
        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            if (context.window != self._window
                    or not _inside_chart_region(self._area, region, event.mouse_x, event.mouse_y)):
                return {"PASS_THROUGH"}
            data = _results.get(context.scene.as_pointer())
            if data:
                frame = plot.clicked_frame(data, region.width, region.height,
                                                    event.mouse_x - region.x, event.mouse_y - region.y)
                if frame is not None:
                    context.scene.frame_set(frame)
                    _redraw()
                    return {"RUNNING_MODAL"}
        return {"PASS_THROUGH"}

    def cancel(self, context):
        """Restore the view when Blender cancels the operator."""
        self._close()


class DroneMotionWindowOperator(Operator):
    bl_idname = "drones_anim.open_motion_window"
    bl_label = "打开独立图表窗口"
    bl_description = "复制当前视图区，在Blender独立窗口中查看8项图表"

    @classmethod
    def poll(cls, context):
        """Require a graphical 3D view and a cached result."""
        return (not bpy.app.background and context.area is not None
                and context.area.type == "VIEW_3D" and context.scene.as_pointer() in _results)

    def execute(self, context):
        """Duplicate the current area and show charts in the new window."""
        before = {window.as_pointer() for window in context.window_manager.windows}
        bpy.ops.screen.area_dupli("INVOKE_DEFAULT")
        window = next((w for w in context.window_manager.windows if w.as_pointer() not in before), None)
        if window is None:
            self.report({"WARNING"}, "图表窗口未打开，可使用当前视图显示按钮")
            return {"CANCELLED"}
        area = next((area for area in window.screen.areas if area.type == "VIEW_3D"), None)
        if area is None:
            return {"CANCELLED"}
        region = next(region for region in area.regions if region.type == "WINDOW")
        with context.temp_override(window=window, area=area, region=region):
            bpy.ops.drones_anim.view_motion_analysis("INVOKE_DEFAULT")
        return {"FINISHED"}


class DroneMotionExportOperator(Operator, ExportHelper):
    bl_idname = "drones_anim.export_motion_png"
    bl_label = "导出图表 PNG"
    bl_description = "按当前曲线模式和横轴单位导出完整八项图表"
    filename_ext = ".png"
    filter_glob: StringProperty(default="*.png", options={"HIDDEN"})
    width: IntProperty(name="宽度", default=1600, min=680, max=8192, subtype="PIXEL")
    height: IntProperty(name="高度", default=1200, min=540, max=8192, subtype="PIXEL")

    @classmethod
    def poll(cls, context):
        """Allow PNG export when a cached result is available and no job is running."""
        return (not bpy.app.background and context.scene is not None and not _jobs
                and context.scene.as_pointer() in _results)

    def invoke(self, context, event):
        """Set the default PNG path and open the file browser."""
        if not self.filepath:
            self.filepath = (str(Path(bpy.data.filepath).with_suffix("")) + "_motion.png"
                             if bpy.data.filepath else "drone_motion.png")
        return ExportHelper.invoke(self, context, event)

    def draw(self, context):
        """Show image dimensions in the export dialog."""
        self.layout.prop(self, "width")
        self.layout.prop(self, "height")

    def execute(self, context):
        """Export the cached charts using the current display settings."""
        scene = context.scene
        props = scene.drones_anim_analysis
        destination = bpy.path.abspath(bpy.path.ensure_ext(self.filepath, ".png"))
        try:
            plot.export_png(
                _results[scene.as_pointer()], destination, self.width, self.height,
                props.style, props.time_axis == "SECONDS", scene.frame_current_final,
                _stale(scene, _results[scene.as_pointer()]))
        except Exception as exc:
            self.report({"ERROR"}, f"图表导出失败: {exc}")
            return {"CANCELLED"}
        self.report({"INFO"}, f"已导出图表: {destination}")
        return {"FINISHED"}


class DroneMotionAnalysisPanel(Panel):
    bl_idname = "VIEW3D_PT_drone_motion_analysis"
    bl_label = "全局运动分析"
    bl_parent_id = "OBJECT_PT_drones_anim_panel"
    bl_order = 1
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "无人机动画"

    def draw(self, context):
        """Draw analysis controls, progress and cached result details."""
        layout, scene = self.layout, context.scene
        props = scene.drones_anim_analysis
        job = _jobs.get(scene.as_pointer())
        busy = job is not None
        row = layout.row()
        row.enabled = not busy
        row.prop(props, "background")
        layout.operator(DroneMotionCalculateOperator.bl_idname,
                        text="计算中…（Esc取消）" if busy else "计算全局运动曲线")
        if busy:
            layout.progress(factor=job._progress, type="BAR", text=f"计算进度：{job._progress:.0%}")
        layout.prop(props, "style")
        row = layout.row()
        row.label(text="横轴")
        row.prop(props, "time_axis", expand=True)
        row = layout.row()
        row.enabled = not busy
        row.operator(DroneMotionViewOperator.bl_idname)
        row = layout.row()
        row.enabled = not busy
        row.operator(DroneMotionWindowOperator.bl_idname)
        layout.operator(DroneMotionExportOperator.bl_idname, icon="EXPORT")
        data = _results.get(scene.as_pointer())
        if data:
            layout.label(text=f"已缓存：{len(data.names)} 架 / {data.end - data.start + 1} 帧")
            if data.closest_frame is not None:
                layout.label(text=f"最小间距：{data.plots[-1].minimum:.6g} m / 第 {data.closest_frame} 帧")
                layout.label(text=" / ".join(data.closest_pair))
            if _stale(scene, data):
                layout.label(text="帧率或范围已变，请重新计算", icon="ERROR")


def _stale(scene, data):
    """Check whether the scene range or frame rate has changed."""
    return (scene.frame_start != data.start or scene.frame_end != data.end
            or abs(scene.render.fps / scene.render.fps_base - data.fps) > 1e-9)


def _inside_chart_region(area, region, x, y):
    """Overlapping UI regions can lie inside the WINDOW region's rectangle."""
    def contains(candidate):
        """Check whether the point lies inside a visible-sized region."""
        return (candidate.width > 1 and candidate.height > 1
                and candidate.x <= x < candidate.x + candidate.width
                and candidate.y <= y < candidate.y + candidate.height)

    if not contains(region):
        return False
    visibility = {"UI": "show_region_ui", "TOOLS": "show_region_toolbar",
                  "HEADER": "show_region_header", "TOOL_HEADER": "show_region_tool_header",
                  "HUD": "show_region_hud", "ASSET_SHELF": "show_region_asset_shelf",
                  "ASSET_SHELF_HEADER": "show_region_asset_shelf"}
    space = area.spaces.active
    for candidate in area.regions:
        if candidate.type == "WINDOW":
            continue
        flag = visibility.get(candidate.type)
        if flag and not getattr(space, flag, True):
            continue
        if contains(candidate):
            return False
    return True


def _draw():
    """Draw cached charts in an enabled view."""
    context = bpy.context
    if context.area is None or context.area.as_pointer() not in _views:
        return
    data = _results.get(context.scene.as_pointer())
    if data is None:
        return
    props = context.scene.drones_anim_analysis
    plot.draw_analysis(data, context.region.width, context.region.height,
                                props.style, props.time_axis == "SECONDS", context.scene.frame_current_final,
                                _stale(context.scene, data))


def _ensure_draw_handler():
    """Install the chart draw callback once."""
    global _draw_handle
    # Draw after the safety overlay so cached charts remain unobstructed.
    if _draw_handle is None:
        _draw_handle = bpy.types.SpaceView3D.draw_handler_add(_draw, (), "WINDOW", "POST_PIXEL")


@persistent
def _frame_changed(scene, depsgraph=None):
    """Refresh charts after frame changes when no job is running."""
    if not _jobs:
        _redraw()


@persistent
def _loaded(_unused):
    """Close jobs and viewers and clear cached results after loading."""
    for job in list(_jobs.values()):
        try:
            job._cleanup()
        except ReferenceError:
            pass
    _jobs.clear()
    for viewer in list(_view_ops.values()):
        viewer._close()
    _view_ops.clear()
    _results.clear()
    _views.clear()
    plot.clear_cache()


def register():
    """Register analysis settings and scene handlers."""
    Scene.drones_anim_analysis = PointerProperty(type=DroneMotionAnalysisProperties)
    for handlers, callback in ((bpy.app.handlers.frame_change_post, _frame_changed),
                               (bpy.app.handlers.load_post, _loaded)):
        if callback not in handlers:
            handlers.append(callback)


def unregister():
    """Remove analysis settings, handlers and cached resources."""
    global _draw_handle
    _loaded(None)
    for handlers, callback in ((bpy.app.handlers.frame_change_post, _frame_changed),
                               (bpy.app.handlers.load_post, _loaded)):
        if callback in handlers:
            handlers.remove(callback)
    if _draw_handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, "WINDOW")
        _draw_handle = None
    if hasattr(Scene, "drones_anim_analysis"):
        del Scene.drones_anim_analysis
