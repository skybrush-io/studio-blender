import json
import math
import os
import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, FloatVectorProperty, IntProperty, StringProperty
from bpy.types import Operator
from numpy import array, column_stack, mgrid, repeat, tile, zeros

from sbstudio.model.types import Coordinate3D
from sbstudio.plugin.colors import create_keyframe_for_color_of_drone
from sbstudio.plugin.constants import Collections, Formations, Templates
from sbstudio.plugin.materials import get_material_for_pyro
from sbstudio.plugin.model.formation import add_points_to_formation, create_formation
from sbstudio.plugin.model.storyboard import StoryboardEntryPurpose, get_storyboard
from sbstudio.plugin.operators.detach_materials_from_template import (
    detach_pyro_material_from_drone_template,
)
from sbstudio.plugin.selection import select_only
from sbstudio.plugin.utils import propose_names
from sbstudio.plugin.utils.bloom import enable_bloom_effect_if_needed

__all__ = (
    "CreateTakeoffGridOperator",
    "ExportBoxPresetOperator",
    "ApplyGridLayoutOperator",
    "ApplyBoxParamsOperator",
    "SetDroneCoordOperator",
)


# Translation dictionary for Box Preset
# IMPORTANT: Blender 4.x uses "zh_HANS" for Simplified Chinese (not "zh_CN").
# We register the same dict under both keys for forward/backward compatibility.
_zh_translations = {
    ("*", "Box Preset"): "箱起预设",
    ("*", "Drone Count"): "无人机数量",
    ("*", "Boxes Count"): "箱数",
    ("*", "Boxes C..."): "箱数",
    ("*", "Rows"): "行数",
    ("*", "Columns"): "列数",
    ("*", "Orientation"): "方向",
    ("*", "Traverse Mode"): "遍历方式",
    ("*", "X Spacing"): "X间距",
    ("*", "Y Spacing"): "Y间距",
    ("*", "Y S..."): "Y间距",
    ("*", "Export Preset"): "导出预设",
    ("*", "Adjust Box Parameters"): "调整箱起参数",
    ("*", "Adjust Box P..."): "调整箱起参数",
    ("*", "Apply"): "应用",
    ("*", "Apply Grid Layout"): "应用网格布局",
    ("*", "Vertical"): "垂直",
    ("*", "Horizontal"): "水平",
    ("*", "Row Major"): "按行优先",
    ("*", "Column Major"): "按列优先",
    ("*", "Zigzag"): "之字形",
    ("*", "Drones per box"): "每箱无人机数",
    ("*", "Layout"): "布局",
    ("*", "Layout X"): "布局X",
    ("*", "Layout Y"): "布局Y",
    ("*", "Box Internal Parameters:"): "箱内参数：",
    ("*", "Drone Positions (ID, X, Y, Z):"): "无人机位置（ID, X, Y, Z）：",
    ("Operator", "Apply"): "应用",
    ("*", "Box Array Layering"): "箱式阵列分层",
    ("*", "Box Layer Scheme"): "箱式分层方案",
    ("*", "Box Layer S..."): "箱式分层方案",
    ("*", "Traditional Array Layering"): "单机阵列分层",
    ("*", "Traditional Layer Scheme"): "单机分层方案",
    ("*", "Traditional Layer ..."): "单机分层方案",
    ("*", "Batch Takeoff"): "分组起飞",
    ("*", "Traditional Array Batch Takeoff"): "单机阵列分组起飞",
    ("*", "Trad Start Frame"): "单机起飞帧",
    ("*", "Trad Start Fr..."): "单机起飞帧",
    ("*", "Auto"): "自动",
    ("*", "8-Layer"): "8层",
    ("*", "12-Layer"): "12层",
    ("*", "16-Layer"): "16层",
    ("*", "4-Layer"): "4层",
    ("*", "9-Layer"): "9层",
    ("*", "Drone Group Filter"): "无人机分组筛选",
    ("*", "Drone Group"): "无人机分组",
    ("*", "Limit to"): "限制到",
    ("*", "All drones"): "所有无人机",
    ("*", "Box array only"): "仅箱式阵列",
    ("*", "Traditional array only"): "仅单机阵列",
    ("*", "Return Group"): "返航分组",
    ("*", "with Velocity"): "速度",
    ("*", "to Altitude"): "高度",
    ("*", "Layer height"): "层高",
    ("*", "Mixed Mode"): "混合模式",
    ("*", "Mixed Gap"): "阵列间距",
    ("*", "Mixed Position"): "位置",
    ("*", "Advanced"): "高级",
    ("*", "Single-Drone Array Below Box Array"): "单机阵列在箱式阵列下方",
    ("*", "Single-Drone Array Above Box Array"): "单机阵列在箱式阵列上方",
    ("*", "Single-Drone Array Left of Box Array"): "单机阵列在箱式阵列左侧",
    ("*", "Single-Drone Array Right of Box Array"): "单机阵列在箱式阵列右侧",
    ("*", "Box Array Below Single-Drone Array"): "箱式阵列在单机阵列下方",
    ("*", "Box Array Above Single-Drone Array"): "箱式阵列在单机阵列上方",
    ("*", "Box Array Left of Single-Drone Array"): "箱式阵列在单机阵列左侧",
    ("*", "Box Array Right of Single-Drone Array"): "箱式阵列在单机阵列右侧",
    ("*", "Enable Mixed Mode (Single + Box)"): "启用混合模式（同时生成单机+箱式）",
    ("*", "Single/Box Array Gap"): "单机阵列与箱式阵列间距",
    ("*", "Spacing"): "间隔",
}

_ja_translations = {
    ("*", "Box Preset"): "ボックスプリセット",
    ("*", "Drone Count"): "ドローン数",
    ("*", "Boxes Count"): "ボックス数",
    ("*", "Boxes C..."): "ボックス数",
    ("*", "Rows"): "行数",
    ("*", "Columns"): "列数",
    ("*", "Orientation"): "向き",
    ("*", "Traverse Mode"): "走査モード",
    ("*", "X Spacing"): "X間隔",
    ("*", "Y Spacing"): "Y間隔",
    ("*", "Y S..."): "Y間隔",
    ("*", "Export Preset"): "プリセット書き出し",
    ("*", "Adjust Box Parameters"): "ボックスパラメータ調整",
    ("*", "Adjust Box P..."): "ボックスパラメータ調整",
    ("*", "Apply"): "適用",
    ("*", "Apply Grid Layout"): "グリッドレイアウト適用",
    ("*", "Vertical"): "垂直",
    ("*", "Horizontal"): "水平",
    ("*", "Row Major"): "行優先",
    ("*", "Column Major"): "列優先",
    ("*", "Zigzag"): "ジグザグ",
    ("*", "Drones per box"): "ボックスあたりドローン数",
    ("*", "Layout"): "レイアウト",
    ("*", "Layout X"): "レイアウトX",
    ("*", "Layout Y"): "レイアウトY",
    ("*", "Box Internal Parameters:"): "ボックス内部パラメータ：",
    ("*", "Drone Positions (ID, X, Y, Z):"): "ドローン位置（ID, X, Y, Z）：",
    ("Operator", "Apply"): "適用",
    ("*", "Box Array Layering"): "ボックス配列レイヤリング",
    ("*", "Box Layer Scheme"): "ボックスレイヤー方式",
    ("*", "Box Layer S..."): "ボックスレイヤー方式",
    ("*", "Traditional Array Layering"): "従来配列レイヤリング",
    ("*", "Traditional Layer Scheme"): "従来レイヤー方式",
    ("*", "Traditional Layer ..."): "従来レイヤー方式",
    ("*", "Batch Takeoff"): "グループ離陸",
    ("*", "Traditional Array Batch Takeoff"): "従来配列グループ離陸",
    ("*", "Trad Start Frame"): "従来開始フレーム",
    ("*", "Trad Start Fr..."): "従来開始フレーム",
    ("*", "Auto"): "自動",
    ("*", "8-Layer"): "8層",
    ("*", "12-Layer"): "12層",
    ("*", "16-Layer"): "16層",
    ("*", "4-Layer"): "4層",
    ("*", "9-Layer"): "9層",
    ("*", "Drone Group Filter"): "ドローングループフィルター",
    ("*", "Drone Group"): "ドローングループ",
    ("*", "Limit to"): "制限",
    ("*", "All drones"): "全ドローン",
    ("*", "Box array only"): "ボックス配列のみ",
    ("*", "Traditional array only"): "従来配列のみ",
    ("*", "Return Group"): "帰還グループ",
    ("*", "with Velocity"): "速度",
    ("*", "to Altitude"): "高度",
    ("*", "Layer height"): "レイヤー高さ",
    ("*", "Mixed Mode"): "ミックスモード",
    ("*", "Mixed Gap"): "配列間隔",
    ("*", "Mixed Position"): "配置位置",
    ("*", "Advanced"): "詳細設定",
    ("*", "Single-Drone Array Below Box Array"): "単機配列がボックス配列の下",
    ("*", "Single-Drone Array Above Box Array"): "単機配列がボックス配列の上",
    ("*", "Single-Drone Array Left of Box Array"): "単機配列がボックス配列の左",
    ("*", "Single-Drone Array Right of Box Array"): "単機配列がボックス配列の右",
    ("*", "Box Array Below Single-Drone Array"): "ボックス配列が単機配列の下",
    ("*", "Box Array Above Single-Drone Array"): "ボックス配列が単機配列の上",
    ("*", "Box Array Left of Single-Drone Array"): "ボックス配列が単機配列の左",
    ("*", "Box Array Right of Single-Drone Array"): "ボックス配列が単機配列の右",
    ("*", "Enable Mixed Mode (Single + Box)"): "ミックスモード有効（単機+ボックス）",
    ("*", "Single/Box Array Gap"): "単機/ボックス配列間隔",
    ("*", "Spacing"): "間隔",
}

translations_dict = {
    "zh_HANS": _zh_translations,
    "zh_CN": _zh_translations,
    "ja_JP": _ja_translations,
}


# === Starlight Box Preset Constants ===
# Box offsets: 8 positions relative to box center
# Vertical orientation: 2 cols x 4 rows
BOX_OFFSETS_VERTICAL = [
    (-0.18, -0.545),
    (0.18, -0.545),
    (-0.18, -0.215),
    (0.18, -0.215),
    (-0.18, 0.165),
    (0.18, 0.165),
    (-0.18, 0.495),
    (0.18, 0.495),
]

# Horizontal orientation: swap x/y
BOX_OFFSETS_HORIZONTAL = [(y, x) for (x, y) in BOX_OFFSETS_VERTICAL]

# Default box preset (E4mini)
DEFAULT_BOX_PRESET = {
    "name": "E4mini",
    "drones_per_box": 8,
    "layout": "2x4",  # 2 columns x 4 rows
    "offsets": BOX_OFFSETS_VERTICAL,
}


def create_drone(location, *, name: str, template=None, collection=None):
    """Creates a new drone object at the given location.

    Parameters:
        location: the location where the drone should be created
        name: the name of the drone
        template: the template object to use for the mesh of the drone;
            `None` to use the default drone template
        collection: the collection that the drone should be a part of; use
            `None` to add it to the default drone collection
    """
    template = template or Templates.find_drone()
    collection = collection or Collections.find_drones()

    drone = template.copy()
    drone.data = template.data.copy()
    drone.name = name
    drone.location = location

    # The template might be hidden; let's make sure that we are visible even
    # if the template is hidden
    drone.hide_render = False
    drone.hide_select = False
    drone.hide_viewport = False

    collection.objects.link(drone)

    return drone


def create_points_of_takeoff_grid(
    center: Coordinate3D,
    rows: int = 1,
    columns: int = 1,
    num_drones_per_slot_row: int = 1,
    num_drones_per_slot_col: int = 1,
    spacing_row: float = 1,
    spacing_col: float = 1,
    intra_slot_spacing_row: float = 0.5,
    intra_slot_spacing_col: float = 0.5,
) -> list[Coordinate3D]:
    """Creates the points of a takeoff grid centered at the given coordinate.

    Parameters:
        center: the center of the takeoff grid
        rows: the number of rows in the grid
        columns: the number of columns in the grid
        num_drones_per_slot_row: the number of drones in a single grid slot row
        num_drones_per_slot_col: the number of drones in a single grid slot column
        spacing_row: the row spacing of points in the grid
        spacing_col: the column spacing of points in the grid
        intra_slot_spacing_row: the row spacing within a single slot of the grid
        intra_slot_spacing_col: the column spacing within a single slot of the grid

    Returns:
        the list of points in the grid
    """
    columns = max(columns, 0)
    rows = max(rows, 0)

    cx, cy, cz = center

    xs, ys = mgrid[0:columns, 0:rows]

    xs = (xs.ravel() - (columns - 1) / 2) * spacing_col + cx
    ys = (ys.ravel() - (rows - 1) / 2) * spacing_row + cy
    zs = cz + zeros(columns * rows)

    # At this point we have the coordinates of the cells in the grid. Replace
    # each cell with multiple drones if needed
    if num_drones_per_slot_row > 1 or num_drones_per_slot_col > 1:
        num_drones_per_slot = num_drones_per_slot_row * num_drones_per_slot_col
        # Calculate the ranges for x and y based on the number of drones
        x_range = [
            x - num_drones_per_slot_col // 2 for x in range(num_drones_per_slot_col)
        ]
        y_range = [
            y - num_drones_per_slot_row // 2 for y in range(num_drones_per_slot_row)
        ]

        # Adjust for even numbers to symmetrically distribute around the center
        if num_drones_per_slot_col % 2 == 0:
            x_range = [x + 0.5 for x in x_range]
        if num_drones_per_slot_row % 2 == 0:
            y_range = [y + 0.5 for y in y_range]

        slot_template = array(
            [
                [x * intra_slot_spacing_col, y * intra_slot_spacing_row]
                for y in y_range
                for x in x_range
            ]
        )
        template = column_stack((slot_template, zeros((len(slot_template), 1))))

        coords = repeat(column_stack((xs, ys, zs)), num_drones_per_slot, axis=0)
        coords += tile(template, (columns * rows, 1))
        xs, ys, zs = coords[:, 0], coords[:, 1], coords[:, 2]

    return list(zip(xs, ys, zs))


# === Starlight Box Preset Functions ===


def get_box_offsets(orientation):
    """Return the box offsets for the given orientation."""
    if orientation == "HORIZONTAL":
        return BOX_OFFSETS_HORIZONTAL
    return BOX_OFFSETS_VERTICAL


def compute_box_size(offsets, diameter):
    """Compute box width and height from offsets and drone diameter."""
    xs = [o[0] for o in offsets]
    ys = [o[1] for o in offsets]
    width = max(xs) - min(xs) + diameter
    height = max(ys) - min(ys) + diameter
    return width, height


def build_traverse_order(rows, cols, mode):
    """Build traverse order for box grid."""
    order = []
    if mode == "ROW":
        for r in range(rows):
            for c in range(cols):
                order.append((r, c))
    elif mode == "COL":
        for c in range(cols):
            for r in range(rows):
                order.append((r, c))
    elif mode == "ZIGZAG":
        for r in range(rows):
            col_range = range(cols) if r % 2 == 0 else range(cols - 1, -1, -1)
            for c in col_range:
                order.append((r, c))
    return order


def create_box_preset_grid(
    center: Coordinate3D,
    box_drone_count: int,
    box_grid_rows: int,
    box_grid_cols: int,
    box_orientation: str,
    box_traverse: str,
    box_spacing_x: float,
    box_spacing_y: float,
    drone_diameter: float,
    custom_offsets=None,
    drones_per_box: int = 8,
) -> list:
    """Create takeoff grid using Starlight Box Preset logic.

    Parameters:
        center: the center of the takeoff grid
        box_drone_count: total number of drones
        box_grid_rows: number of box rows
        box_grid_cols: number of box columns
        box_orientation: "VERTICAL" or "HORIZONTAL"
        box_traverse: traversal order "ROW", "COL" or "ZIGZAG"
        box_spacing_x: spacing between boxes in X (edge-to-edge)
        box_spacing_y: spacing between boxes in Y (edge-to-edge)
        drone_diameter: diameter of a drone (for size computation)
        custom_offsets: optional list of (x, y) custom offsets per drone in a box
        drones_per_box: number of drones per box (default 8)
    """
    drones_per_box = max(1, int(drones_per_box))
    num_boxes = math.ceil(box_drone_count / drones_per_box)

    if custom_offsets and len(custom_offsets) >= drones_per_box:
        offsets = list(custom_offsets[:drones_per_box])
    else:
        offsets = get_box_offsets(box_orientation)[:drones_per_box]

    box_w, box_h = compute_box_size(offsets, drone_diameter)

    rows = box_grid_rows
    cols = box_grid_cols

    center_spacing_x = box_w + box_spacing_x
    center_spacing_y = box_h + box_spacing_y

    total_w = (cols - 1) * center_spacing_x
    total_h = (rows - 1) * center_spacing_y

    box_order = build_traverse_order(rows, cols, box_traverse)

    cx, cy, cz = center
    points = []
    drones_remaining = box_drone_count

    for box_idx, (r, c) in enumerate(box_order):
        if box_idx >= num_boxes or drones_remaining <= 0:
            break

        box_cx = c * center_spacing_x - total_w / 2.0 + cx
        box_cy = -(r * center_spacing_y - total_h / 2.0) + cy

        slots_in_box = min(drones_per_box, drones_remaining)
        for slot in range(slots_in_box):
            ox, oy = offsets[slot]
            points.append((box_cx + ox, box_cy + oy, cz))
            drones_remaining -= 1

    return points


def export_box_preset(filepath, offsets, drones_per_box=8, layout="2x4", name="Custom"):
    """Export box preset to TXT file."""
    data = {
        "name": name,
        "drones_per_box": drones_per_box,
        "layout": layout,
        "offsets": offsets,
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"# Box Preset: {name}\n")
        f.write(f"# Drones per box: {drones_per_box}\n")
        f.write(f"# Layout: {layout}\n")
        f.write(f"#\n")
        f.write(f"# Format: Drone_ID, X, Y, Z\n")
        f.write(f"# Coordinates are relative to box center\n")
        f.write(f"#\n\n")

        for i, (x, y) in enumerate(offsets):
            f.write(f"{i+1}, {x:.4f}, {y:.4f}, 0.0000\n")

        f.write(f"\n# JSON Data (for import):\n")
        f.write(f"# {json.dumps(data)}\n")


def import_box_preset(filepath):
    """Import box preset from TXT file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        if "# JSON Data" in content:
            json_line = [line for line in content.split('\n') if line.startswith('# {')]
            if json_line:
                json_str = json_line[0][2:]
                data = json.loads(json_str)
                return data

        offsets = []
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 3:
                try:
                    x = float(parts[1])
                    y = float(parts[2])
                    offsets.append((x, y))
                except ValueError:
                    continue

        if offsets:
            return {
                "name": "Custom",
                "drones_per_box": len(offsets),
                "layout": f"{len(set(x for x, y in offsets))}x{len(set(y for x, y in offsets))}",
                "offsets": offsets,
            }

        return None
    except Exception as e:
        print(f"Error importing box preset: {e}")
        return None


# === Box Preset Update Callbacks ===

_UPDATE_LOCK = False


def _distribute_boxes_to_grid(boxes):
    """Distribute boxes into a near-square grid layout."""
    boxes = max(1, int(boxes))
    cols = max(1, int(round(math.sqrt(boxes))))
    rows = math.ceil(boxes / cols)
    best_cols = cols
    best_rows = rows
    best_diff = rows * cols - boxes
    for c in range(max(1, cols - 2), cols + 3):
        r = math.ceil(boxes / c)
        diff = r * c - boxes
        if diff == 0 and (best_diff != 0 or abs(r - c) < abs(best_rows - best_cols)):
            best_cols, best_rows, best_diff = c, r, diff
        elif best_diff != 0 and diff < best_diff:
            best_cols, best_rows, best_diff = c, r, diff
    return best_rows, best_cols


def _update_box_drone_count(self, context):
    """Sync boxes count and grid layout when drone count changes."""
    global _UPDATE_LOCK
    if _UPDATE_LOCK or not self.use_advanced_settings:
        return
    _UPDATE_LOCK = True
    try:
        drones_per_box = getattr(self, "drones_per_box", 8)
        boxes = max(1, math.ceil(self.box_drone_count / drones_per_box))
        if self.box_boxes_count != boxes:
            self.box_boxes_count = boxes
        rows, cols = _distribute_boxes_to_grid(boxes)
        if self.box_grid_rows != rows:
            self.box_grid_rows = rows
        if self.box_grid_cols != cols:
            self.box_grid_cols = cols
    finally:
        _UPDATE_LOCK = False


def _update_box_boxes_count(self, context):
    """Sync drone count and grid layout when box count changes."""
    global _UPDATE_LOCK
    if _UPDATE_LOCK or not self.use_advanced_settings:
        return
    _UPDATE_LOCK = True
    try:
        drones_per_box = getattr(self, "drones_per_box", 8)
        drones = self.box_boxes_count * drones_per_box
        if self.box_drone_count != drones:
            self.box_drone_count = drones
        rows, cols = _distribute_boxes_to_grid(self.box_boxes_count)
        if self.box_grid_rows != rows:
            self.box_grid_rows = rows
        if self.box_grid_cols != cols:
            self.box_grid_cols = cols
    finally:
        _UPDATE_LOCK = False


def _apply_grid_layout(self, context):
    """Recalculate boxes and drone count from current rows/cols when apply is clicked."""
    global _UPDATE_LOCK
    if _UPDATE_LOCK or not self.use_advanced_settings:
        return
    if not self.apply_grid_layout:
        return
    _UPDATE_LOCK = True
    try:
        rows = max(1, self.box_grid_rows)
        cols = max(1, self.box_grid_cols)
        boxes = rows * cols
        if self.box_boxes_count != boxes:
            self.box_boxes_count = boxes
        drones_per_box = getattr(self, "drones_per_box", 8)
        drones = boxes * drones_per_box
        if self.box_drone_count != drones:
            self.box_drone_count = drones
    finally:
        _UPDATE_LOCK = False
        self.apply_grid_layout = False


# === Mixed Position Enum Items Callback ===

_mixed_position_items_cache = {}


def _mixed_position_items_cb(self, context):
    """Trilingual items callback for mixed_position EnumProperty.

    The returned list is cached to satisfy Blender's requirement that the
    ``items=`` callback always returns a stable reference.
    """
    try:
        locale = bpy.app.translations.locale or ""
    except Exception:
        locale = ""
    if locale.startswith("zh"):
        key = "zh"
    elif locale.startswith("ja"):
        key = "ja"
    else:
        key = "en"
    cached = _mixed_position_items_cache.get(key)
    if cached is not None:
        return cached
    if key == "zh":
        items = [
            ("TRAD_BELOW", "单机阵列在箱式阵列下方", ""),
            ("TRAD_ABOVE", "单机阵列在箱式阵列上方", ""),
            ("TRAD_LEFT", "单机阵列在箱式阵列左侧", ""),
            ("TRAD_RIGHT", "单机阵列在箱式阵列右侧", ""),
            ("BOX_BELOW", "箱式阵列在单机阵列下方", ""),
            ("BOX_ABOVE", "箱式阵列在单机阵列上方", ""),
            ("BOX_LEFT", "箱式阵列在单机阵列左侧", ""),
            ("BOX_RIGHT", "箱式阵列在单机阵列右侧", ""),
        ]
    elif key == "ja":
        items = [
            ("TRAD_BELOW", "単機配列がボックス配列の下", ""),
            ("TRAD_ABOVE", "単機配列がボックス配列の上", ""),
            ("TRAD_LEFT", "単機配列がボックス配列の左", ""),
            ("TRAD_RIGHT", "単機配列がボックス配列の右", ""),
            ("BOX_BELOW", "ボックス配列が単機配列の下", ""),
            ("BOX_ABOVE", "ボックス配列が単機配列の上", ""),
            ("BOX_LEFT", "ボックス配列が単機配列の左", ""),
            ("BOX_RIGHT", "ボックス配列が単機配列の右", ""),
        ]
    else:
        items = [
            ("TRAD_BELOW", "Single-Drone Array Below Box Array", ""),
            ("TRAD_ABOVE", "Single-Drone Array Above Box Array", ""),
            ("TRAD_LEFT", "Single-Drone Array Left of Box Array", ""),
            ("TRAD_RIGHT", "Single-Drone Array Right of Box Array", ""),
            ("BOX_BELOW", "Box Array Below Single-Drone Array", ""),
            ("BOX_ABOVE", "Box Array Above Single-Drone Array", ""),
            ("BOX_LEFT", "Box Array Left of Single-Drone Array", ""),
            ("BOX_RIGHT", "Box Array Right of Single-Drone Array", ""),
        ]
    _mixed_position_items_cache[key] = items
    return items


def _get_num_drones_per_slot(operator):
    return _get_num_drones_per_slot_row(operator) * _get_num_drones_per_slot_col(
        operator
    )


def _get_num_drones_per_slot_row(operator):
    if hasattr(operator, "drones_per_slot_row"):
        return max(1, operator.drones_per_slot_row)
    else:
        # backwards compatibility
        return 1


def _get_num_drones_per_slot_col(operator):
    if hasattr(operator, "drones_per_slot_col"):
        return max(1, operator.drones_per_slot_col)
    else:
        # backwards compatibility
        return 1


def _get_max_possible_drone_count(operator):
    return operator.rows * operator.columns * _get_num_drones_per_slot(operator)


def _ensure_rows_columns_and_counts_consistent(operator, context):
    max_possible_drone_count = _get_max_possible_drone_count(operator)
    num_drones = max_possible_drone_count - operator.empty_slots
    if num_drones < 1:
        operator.drones = 1
        operator.empty_slots = max(0, max_possible_drone_count)
    else:
        # condition needed to prevent recursion
        if operator.drones != num_drones:
            operator.drones = num_drones


def _handle_drone_count_change(operator, context):
    max_possible_drone_count = _get_max_possible_drone_count(operator)
    operator.empty_slots = max(0, max_possible_drone_count - operator.drones)
    _ensure_rows_columns_and_counts_consistent(operator, context)


def _handle_drones_per_slot_change(operator, context):
    _ensure_rows_columns_and_counts_consistent(operator, context)


class CreateTakeoffGridOperator(Operator):
    """Blender operator that creates the takeoff grid and the corresponding set
    of drones.
    """

    bl_idname = "skybrush.create_takeoff_grid"
    bl_label = "Create Takeoff Grid"
    bl_description = "Creates the takeoff grid and the corresponding set of drones"
    bl_options = {"REGISTER", "UNDO"}

    rows = IntProperty(
        name="Rows",
        description="Number of rows in the takeoff grid",
        default=8,
        soft_min=1,
        soft_max=100,
        update=_ensure_rows_columns_and_counts_consistent,
    )

    columns = IntProperty(
        name="Columns",
        description="Number of columns in the takeoff grid",
        default=8,
        soft_min=1,
        soft_max=100,
        update=_ensure_rows_columns_and_counts_consistent,
    )

    drones = IntProperty(
        name="Drone count",
        description="Number of drones in the grid",
        default=64,
        soft_min=1,
        soft_max=10000,
        update=_handle_drone_count_change,
    )

    # Name is a misnomer, should be excess_drones, but we have to leave it
    # for sake of backward compatibility
    empty_slots = IntProperty(
        name="Number of drones that could be placed in the slots but are not needed",
        default=0,
        options={"HIDDEN"},
    )

    spacing = FloatProperty(
        name="Spacing",
        description="Spacing between the slots in the grid",
        default=3,
        soft_min=0,
        soft_max=50,
        unit="LENGTH",
    )

    use_advanced_settings = BoolProperty(
        name="Advanced",
        default=False,
        description="Advanced settings for creating the takeoff grid",
    )

    # === Starlight Box Preset Properties ===

    use_mixed_mode = BoolProperty(
        name="Mixed Mode",
        default=False,
        description="Generate both box preset and traditional grid simultaneously",
    )

    mixed_gap = FloatProperty(
        name="Mixed Gap",
        description="Gap between box group and traditional group",
        default=2.0,
        min=0.0,
        soft_max=100.0,
        unit="LENGTH",
    )

    mixed_position = EnumProperty(
        name="Mixed Position",
        description="Position of traditional group relative to box group",
        items=_mixed_position_items_cb,
    )

    box_drone_count = IntProperty(
        name="Drone Count",
        description="Total number of drones in the box grid",
        default=48,
        min=0,
        soft_max=10000,
        update=_update_box_drone_count,
    )

    box_boxes_count = IntProperty(
        name="Boxes Count",
        description="Number of boxes in the grid",
        default=6,
        min=1,
        soft_max=1000,
        update=_update_box_boxes_count,
    )

    box_grid_rows = IntProperty(
        name="Rows",
        description="Number of rows in the box grid",
        default=2,
        min=1,
        soft_max=100,
    )

    box_grid_cols = IntProperty(
        name="Columns",
        description="Number of columns in the box grid",
        default=3,
        min=1,
        soft_max=100,
    )

    apply_grid_layout = BoolProperty(
        name="Apply Grid Layout",
        description="Apply rows and columns to boxes and drone count",
        default=False,
        update=_apply_grid_layout,
    )

    drones_per_box = IntProperty(
        name="Drones per Box",
        description="Number of drones in each box (from preset)",
        default=8,
        min=1,
        max=100,
        options={'HIDDEN'},
    )

    custom_box_offsets = StringProperty(
        name="Custom Box Offsets",
        description="Custom box offsets (JSON format)",
        default="",
        options={'HIDDEN'},
    )

    box_orientation = EnumProperty(
        name="Orientation",
        description="Box orientation (vertical 2x4 or horizontal 4x2)",
        items=[
            ("VERTICAL", "Vertical", "2 cols x 4 rows per box"),
            ("HORIZONTAL", "Horizontal", "4 cols x 2 rows per box"),
        ],
        default="VERTICAL",
    )

    box_traverse = EnumProperty(
        name="Traverse Mode",
        description="Box traversal order",
        items=[
            ("ROW", "Row Major", "Left to right, top to bottom"),
            ("COL", "Column Major", "Top to bottom, left to right"),
            ("ZIGZAG", "Zigzag", "Alternating row direction"),
        ],
        default="ROW",
    )

    box_spacing_x = FloatProperty(
        name="X Spacing",
        description="Spacing between boxes in X direction (edge-to-edge)",
        default=0.6,
        min=0.0,
        soft_max=50.0,
        unit="LENGTH",
    )

    box_spacing_y = FloatProperty(
        name="Y Spacing",
        description="Spacing between boxes in Y direction (edge-to-edge)",
        default=0.6,
        min=0.0,
        soft_max=50.0,
        unit="LENGTH",
    )

    show_box_params = BoolProperty(
        name="Adjust Box Parameters",
        default=False,
        description="Show and edit box internal parameters",
    )

    edit_drones_per_box = IntProperty(
        name="Drones per box",
        description="Number of drones in each box",
        default=8,
        min=1,
        max=100,
    )

    edit_box_layout_x = IntProperty(
        name="Layout X",
        description="Number of columns in box layout",
        default=2,
        min=1,
        max=10,
    )

    edit_box_layout_y = IntProperty(
        name="Layout Y",
        description="Number of rows in box layout",
        default=4,
        min=1,
        max=10,
    )

    # Per-drone XY offsets (up to 20 drones per box)
    drone_pos_1 = FloatVectorProperty(name="Drone 1", size=2, default=(-0.180, -0.545), precision=3, subtype='XYZ')
    drone_pos_2 = FloatVectorProperty(name="Drone 2", size=2, default=(0.180, -0.545), precision=3, subtype='XYZ')
    drone_pos_3 = FloatVectorProperty(name="Drone 3", size=2, default=(-0.180, -0.215), precision=3, subtype='XYZ')
    drone_pos_4 = FloatVectorProperty(name="Drone 4", size=2, default=(0.180, -0.215), precision=3, subtype='XYZ')
    drone_pos_5 = FloatVectorProperty(name="Drone 5", size=2, default=(-0.180, 0.165), precision=3, subtype='XYZ')
    drone_pos_6 = FloatVectorProperty(name="Drone 6", size=2, default=(0.180, 0.165), precision=3, subtype='XYZ')
    drone_pos_7 = FloatVectorProperty(name="Drone 7", size=2, default=(-0.180, 0.495), precision=3, subtype='XYZ')
    drone_pos_8 = FloatVectorProperty(name="Drone 8", size=2, default=(0.180, 0.495), precision=3, subtype='XYZ')
    drone_pos_9 = FloatVectorProperty(name="Drone 9", size=2, default=(0.0, 0.0), precision=3, subtype='XYZ')
    drone_pos_10 = FloatVectorProperty(name="Drone 10", size=2, default=(0.0, 0.0), precision=3, subtype='XYZ')
    drone_pos_11 = FloatVectorProperty(name="Drone 11", size=2, default=(0.0, 0.0), precision=3, subtype='XYZ')
    drone_pos_12 = FloatVectorProperty(name="Drone 12", size=2, default=(0.0, 0.0), precision=3, subtype='XYZ')
    drone_pos_13 = FloatVectorProperty(name="Drone 13", size=2, default=(0.0, 0.0), precision=3, subtype='XYZ')
    drone_pos_14 = FloatVectorProperty(name="Drone 14", size=2, default=(0.0, 0.0), precision=3, subtype='XYZ')
    drone_pos_15 = FloatVectorProperty(name="Drone 15", size=2, default=(0.0, 0.0), precision=3, subtype='XYZ')
    drone_pos_16 = FloatVectorProperty(name="Drone 16", size=2, default=(0.0, 0.0), precision=3, subtype='XYZ')
    drone_pos_17 = FloatVectorProperty(name="Drone 17", size=2, default=(0.0, 0.0), precision=3, subtype='XYZ')
    drone_pos_18 = FloatVectorProperty(name="Drone 18", size=2, default=(0.0, 0.0), precision=3, subtype='XYZ')
    drone_pos_19 = FloatVectorProperty(name="Drone 19", size=2, default=(0.0, 0.0), precision=3, subtype='XYZ')
    drone_pos_20 = FloatVectorProperty(name="Drone 20", size=2, default=(0.0, 0.0), precision=3, subtype='XYZ')

    # advanced parameters below (preserved from upstream for backward compatibility)

    use_separate_column_spacing = BoolProperty(
        name="Use seperate column spacing",
        default=False,
        description="When checked, a separate column spacing will be used for the takeoff grid",
    )

    spacing_col = FloatProperty(
        name="Column spacing",
        description="Spacing between the columns of the slots in the grid",
        default=3,
        soft_min=0,
        soft_max=50,
        unit="LENGTH",
    )

    drones_per_slot_row = IntProperty(
        name="Intra-slot rows",
        description=("Number of rows in a single slot"),
        default=1,
        soft_min=1,
        soft_max=10,
        update=_handle_drones_per_slot_change,
    )

    drones_per_slot_col = IntProperty(
        name="Intra-slot columns",
        description=("Number of columns in a single slot"),
        default=1,
        soft_min=1,
        soft_max=10,
        update=_handle_drones_per_slot_change,
    )

    intra_slot_spacing_row = FloatProperty(
        name="Intra-slot row spacing",
        description="Row spacing between drones within each slot",
        default=0.5,
        soft_min=0,
        soft_max=5,
        unit="LENGTH",
    )

    intra_slot_spacing_col = FloatProperty(
        name="Intra-slot column spacing",
        description="Column spacing between drones within each slot",
        default=0.5,
        soft_min=0,
        soft_max=5,
        unit="LENGTH",
    )

    def _get_locale(self):
        """Return current locale code: 'zh' / 'ja' / 'en'."""
        try:
            locale = bpy.app.translations.locale or ""
        except Exception:
            locale = ""
        if locale.startswith("zh"):
            return "zh"
        elif locale.startswith("ja"):
            return "ja"
        return "en"

    def _is_chinese(self):
        """Return True if Blender's current language is Chinese."""
        return self._get_locale() == "zh"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.ui_units_x = 18

        lang = self._get_locale()
        zh = (lang == "zh")
        ja = (lang == "ja")

        def _t(zh_s, ja_s, en_s):
            if zh:
                return zh_s
            if ja:
                return ja_s
            return en_s

        L = {
            "advanced": _t("高级", "詳細設定", "Advanced"),
            "box_preset": _t("箱起预设", "ボックスプリセット", "Box Preset"),
            "drone_count": _t("无人机数量", "ドローン数", "Drone Count"),
            "boxes_count": _t("无人机箱数", "ボックス数", "Boxes Count"),
            "rows": _t("行数", "行数", "Rows"),
            "cols": _t("列数", "列数", "Columns"),
            "orientation": _t("箱内方向", "向き", "Orientation"),
            "traverse": _t("布局模式", "走査モード", "Traverse Mode"),
            "x_spacing": _t("X 间距", "X間隔", "X Spacing"),
            "y_spacing": _t("Y 间距", "Y間隔", "Y Spacing"),
            "adjust_params": _t("调整箱起预设参数", "ボックスパラメータ調整", "Adjust Box Parameters"),
            "internal_params": _t("箱体内参数", "ボックス内部パラメータ", "Box Internal Parameters"),
            "drones_per_box": _t("一箱无人机的数量", "ボックスあたりドローン数", "Drones per box"),
            "layout": _t("箱内布局", "レイアウト", "Layout"),
            "positions": _t("无人机坐标", "ドローン位置", "Drone Positions"),
            "apply": _t("应用", "適用", "Apply"),
            "basic_rows": _t("行", "行", "Rows"),
            "basic_cols": _t("列", "列", "Columns"),
            "basic_drones": _t("无人机数量", "ドローン数", "Drone Count"),
            "basic_spacing": _t("间隔", "間隔", "Spacing"),
            "single_array": _t("单机阵列", "単機配列", "Single-Drone Array"),
            "box_array": _t("箱式阵列", "ボックス配列", "Box Array"),
            "mixed_mode_section": _t("混合模式", "ミックスモード", "Mixed Mode"),
            "mixed_mode": _t("启用混合模式（同时生成单机+箱式）", "ミックスモード有効（単機+ボックス）", "Enable Mixed Mode (Single + Box)"),
            "mixed_gap": _t("单机阵列与箱式阵列间距", "単機/ボックス配列間隔", "Single/Box Array Gap"),
            "mixed_position": _t("位置", "位置", "Position"),
        }

        ICON_SINGLE = 'MESH_GRID'
        ICON_BOX = 'PACKAGE'
        ICON_MIXED = 'OVERLAY'

        # ========== Single-Drone Array ==========
        header = layout.row()
        header.label(text=L["single_array"], icon=ICON_SINGLE)
        layout.prop(self, "rows", text=L["basic_rows"])
        layout.prop(self, "columns", text=L["basic_cols"])
        layout.prop(self, "drones", text=L["basic_drones"])
        layout.prop(self, "spacing", text=L["basic_spacing"])

        layout.prop(self, "use_advanced_settings", text=L["advanced"])

        if self.use_advanced_settings:
            # ========== Box Array ==========
            box = layout.box()
            box.use_property_split = False
            header = box.row()
            header.label(text=L["box_array"], icon=ICON_BOX)

            def _label_prop_row(parent, label_text, prop_name, prop_index=-1):
                r = parent.row(align=True)
                r.alignment = 'LEFT'
                label_sub = r.row()
                label_sub.alignment = 'LEFT'
                label_sub.label(text=label_text)
                label_sub.scale_x = 1.5
                r.separator()
                prop_sub = r.row()
                prop_sub.alignment = 'RIGHT'
                if prop_index >= 0:
                    prop_sub.prop(self, prop_name, index=prop_index, text="")
                else:
                    prop_sub.prop(self, prop_name, text="")
                prop_sub.scale_x = 0.6
                return r

            row = box.row()
            sub1 = row.row(align=True)
            sub1.alignment = 'LEFT'
            sub1.label(text=L["drone_count"])
            sub1.prop(self, "box_drone_count", text="")
            sub1.scale_x = 1.2
            row.separator()
            sub2 = row.row(align=True)
            sub2.alignment = 'LEFT'
            sub2.label(text=L["boxes_count"])
            sub2.prop(self, "box_boxes_count", text="")
            sub2.scale_x = 1.2

            drones_per_box = self.drones_per_box
            relation_row = box.row()
            relation_row.alignment = 'CENTER'
            if zh:
                relation_text = f"= {self.box_boxes_count}箱 × {drones_per_box}台"
            elif ja:
                relation_text = f"= {self.box_boxes_count}ボックス × {drones_per_box}機"
            else:
                relation_text = f"= {self.box_boxes_count} boxes × {drones_per_box} drones"
            relation_row.label(text=relation_text)
            relation_row.enabled = False

            row = box.row()
            sub1 = row.row(align=True)
            sub1.alignment = 'LEFT'
            sub1.label(text=L["rows"])
            sub1.prop(self, "box_grid_rows", text="")
            sub1.scale_x = 1.0
            row.separator()
            sub2 = row.row(align=True)
            sub2.alignment = 'LEFT'
            sub2.label(text=L["cols"])
            sub2.prop(self, "box_grid_cols", text="")
            sub2.scale_x = 1.0
            row.prop(self, "apply_grid_layout", text="", icon='CHECKMARK', toggle=True)

            box.prop(self, "box_orientation", text=L["orientation"])
            box.prop(self, "box_traverse", text=L["traverse"])

            box.separator()
            row = box.row()
            sub1 = row.row(align=True)
            sub1.alignment = 'LEFT'
            sub1.label(text=L["x_spacing"])
            sub1.prop(self, "box_spacing_x", text="")
            sub1.scale_x = 1.2
            row.separator()
            sub2 = row.row(align=True)
            sub2.alignment = 'LEFT'
            sub2.label(text=L["y_spacing"])
            sub2.prop(self, "box_spacing_y", text="")
            sub2.scale_x = 1.2

            box.separator()
            box.prop(self, "show_box_params", toggle=True, icon='PREFERENCES', text=L["adjust_params"])

            if self.show_box_params:
                params_box = box.box()
                params_box.use_property_split = False
                params_box.label(text=L["internal_params"] + ("：" if zh or ja else ":"), icon='SETTINGS')

                row = params_box.row()
                row.label(text=L["drones_per_box"] + ("：" if zh or ja else ":"))
                row.prop(self, "edit_drones_per_box", text="")

                row = params_box.row()
                row.label(text=L["layout"] + ("：" if zh or ja else ":"))
                sub = row.row(align=True)
                sub.prop(self, "edit_box_layout_x", text="X")
                sub.prop(self, "edit_box_layout_y", text="Y")

                params_box.separator()
                params_box.label(text=L["positions"] + ("：" if zh or ja else ":"))

                n_drones = min(max(1, self.edit_drones_per_box), 20)
                col_table = params_box.column(align=True)

                header_row = col_table.row(align=True)
                header_row.label(text="")
                header_row.label(text="X")
                header_row.label(text="Y")

                for i in range(n_drones):
                    prop_name = f"drone_pos_{i+1}"
                    if not hasattr(self, prop_name):
                        continue
                    row = col_table.row(align=True)
                    row.label(text=f"Drone {i+1}:")
                    sub = row.row(align=True)
                    sub.prop(self, prop_name, index=0, text="")
                    sub.prop(self, prop_name, index=1, text="")

            # ========== Mixed Mode ==========
            layout.separator()
            mixed_row = layout.row()
            mixed_row.use_property_split = False
            mixed_row.prop(self, "use_mixed_mode", text=L["mixed_mode"], icon=ICON_MIXED)

            if self.use_mixed_mode:
                mixed_box = layout.box()
                mixed_box.prop(self, "mixed_gap", text=L["mixed_gap"])
                mixed_box.prop(self, "mixed_position", text=L["mixed_position"])

    def execute(self, context):
        # This code path is invoked after an undo-redo
        self._run(context)
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
        # The code below is used to trigger the settings panel in the lower
        # left hand corner, see:
        #
        # https://blender.stackexchange.com/questions/191956/how-to-make-custom-create-options-panel-in-bottom-left
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        # This code path is invoked when the user triggers the operator
        self._run(context)
        return {"FINISHED"}

    def _run(self, context):
        bpy.ops.skybrush.prepare()

        settings = context.scene.skybrush.settings

        cx, cy, cz = context.scene.cursor.location
        drone_diameter = settings.drone_radius * 2

        def _generate_traditional_points(center_x, center_y):
            """Generate traditional grid centered at (center_x, center_y)."""
            pts = create_points_of_takeoff_grid(
                center=(center_x, center_y, cz),
                rows=self.rows,
                columns=self.columns,
                num_drones_per_slot_row=_get_num_drones_per_slot_row(self),
                num_drones_per_slot_col=_get_num_drones_per_slot_col(self),
                spacing_row=self.spacing,
                spacing_col=self.spacing_col
                if self.use_separate_column_spacing
                else self.spacing,
                intra_slot_spacing_row=self.intra_slot_spacing_row,
                intra_slot_spacing_col=self.intra_slot_spacing_col,
            )[: self.drones]
            return list(pts)

        def _generate_box_points(center_x, center_y):
            """Generate box preset grid centered at (center_x, center_y)."""
            custom_offsets = None
            drones_per_box_use = self.drones_per_box
            if self.show_box_params:
                drones_per_box_use = max(1, int(self.edit_drones_per_box))
                self.drones_per_box = drones_per_box_use
                custom_offsets = []
                for i in range(drones_per_box_use):
                    prop_name = f"drone_pos_{i+1}"
                    if hasattr(self, prop_name):
                        vec = getattr(self, prop_name)
                        custom_offsets.append((float(vec[0]), float(vec[1])))
                    else:
                        custom_offsets.append((0.0, 0.0))
            return create_box_preset_grid(
                center=(center_x, center_y, cz),
                box_drone_count=self.box_drone_count,
                box_grid_rows=self.box_grid_rows,
                box_grid_cols=self.box_grid_cols,
                box_orientation=self.box_orientation,
                box_traverse=self.box_traverse,
                box_spacing_x=self.box_spacing_x,
                box_spacing_y=self.box_spacing_y,
                drone_diameter=drone_diameter,
                custom_offsets=custom_offsets,
                drones_per_box=drones_per_box_use,
            )

        def _bounding_size(pts):
            if not pts:
                return 0.0, 0.0
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            return (
                max(xs) - min(xs) + drone_diameter,
                max(ys) - min(ys) + drone_diameter,
            )

        scene = context.scene
        scene["sb_mixed_box_count"] = 0
        scene["sb_mixed_trad_count"] = 0
        scene["sb_grid_rows"] = int(self.rows)
        scene["sb_grid_cols"] = int(self.columns)

        if not self.use_advanced_settings:
            # Simple mode (traditional grid only)
            points = _generate_traditional_points(cx, cy)
            scene["sb_mixed_trad_count"] = len(points)
        elif not self.use_mixed_mode:
            # Advanced mode: box preset only
            points = _generate_box_points(cx, cy)
            scene["sb_mixed_box_count"] = len(points)
        else:
            # Mixed mode: box + traditional
            box_pts_local = _generate_box_points(0.0, 0.0)
            trad_pts_local = _generate_traditional_points(0.0, 0.0)

            box_w, box_h = _bounding_size(box_pts_local)
            trad_w, trad_h = _bounding_size(trad_pts_local)

            pos = self.mixed_position
            gap = self.mixed_gap
            box_dx = box_dy = trad_dx = trad_dy = 0.0

            if pos == 'TRAD_LEFT':
                trad_dx = -(box_w / 2.0 + gap + trad_w / 2.0)
            elif pos == 'TRAD_RIGHT':
                trad_dx = box_w / 2.0 + gap + trad_w / 2.0
            elif pos == 'TRAD_ABOVE':
                trad_dy = box_h / 2.0 + gap + trad_h / 2.0
            elif pos == 'TRAD_BELOW':
                trad_dy = -(box_h / 2.0 + gap + trad_h / 2.0)
            elif pos == 'BOX_LEFT':
                box_dx = -(trad_w / 2.0 + gap + box_w / 2.0)
            elif pos == 'BOX_RIGHT':
                box_dx = trad_w / 2.0 + gap + box_w / 2.0
            elif pos == 'BOX_ABOVE':
                box_dy = trad_h / 2.0 + gap + box_h / 2.0
            elif pos == 'BOX_BELOW':
                box_dy = -(trad_h / 2.0 + gap + box_h / 2.0)

            box_pts = [(p[0] + cx + box_dx, p[1] + cy + box_dy, p[2]) for p in box_pts_local]
            trad_pts = [(p[0] + cx + trad_dx, p[1] + cy + trad_dy, p[2]) for p in trad_pts_local]
            points = list(box_pts) + list(trad_pts)
            scene["sb_mixed_box_count"] = len(box_pts)
            scene["sb_mixed_trad_count"] = len(trad_pts)

        drone_template = Templates.find_drone(
            template=settings.drone_template,
            drone_radius=settings.drone_radius,
        )
        drone_collection = Collections.find_drones()

        pyro_template_material = get_material_for_pyro(drone_template)

        box_n = int(scene.get("sb_mixed_box_count", 0))
        trad_n = int(scene.get("sb_mixed_trad_count", 0))

        def _group_for_index(i: int) -> str:
            if box_n > 0 and trad_n > 0:
                return "BOX" if i < box_n else "TRAD"
            elif box_n > 0:
                return "BOX"
            else:
                return "TRAD"

        drones = []
        names = propose_names("Drone {}", len(points))
        for idx, (name, point) in enumerate(zip(names, points)):
            drone = create_drone(
                location=point,
                name=name,
                template=drone_template,
                collection=drone_collection,
            )

            # Tag drone with group for Starlight Animator's grouped takeoff/transitions
            drone["sb_group"] = _group_for_index(idx)

            # The next line is needed for light effects to work properly
            create_keyframe_for_color_of_drone(
                drone, (1.0, 1.0, 1.0), frame=context.scene.frame_start, step=True
            )

            detach_pyro_material_from_drone_template(
                drone, template_material=pyro_template_material
            )

            drones.append(drone)

        select_only(drones)

        enable_bloom_effect_if_needed()

        # Add a new storyboard entry with the initial formation if there is no
        # takeoff grid yet, or extend the existing grid with the new set of
        # points if there is one
        takeoff_grid = Formations.find_takeoff_grid(create=False)
        if not takeoff_grid:
            storyboard = get_storyboard(context=context)
            takeoff_grid_formation = create_formation(Formations.TAKEOFF_GRID, points)
            entry = storyboard.add_new_entry(
                formation=takeoff_grid_formation,
                frame_start=context.scene.frame_start,
                duration=0,
                purpose=StoryboardEntryPurpose.TAKEOFF,
                select=True,
                context=context,
            )
            entry.update_mapping(list(range(len(points))))
            takeoff_grid = takeoff_grid_formation

        else:
            add_points_to_formation(takeoff_grid, points)

        # Reduce marker size for box preset mode (advanced)
        if self.use_advanced_settings and takeoff_grid:
            for obj in takeoff_grid.objects:
                if obj.type == 'EMPTY':
                    obj.empty_display_size *= 0.35

        # Report generation result
        if points:
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            drone_radius = settings.drone_radius
            width = (max(xs) - min(xs)) + drone_radius * 2
            height = (max(ys) - min(ys)) + drone_radius * 2
            area = width * height
            if self._is_chinese():
                msg = f"已生成 {len(points)} 架无人机。区域：{width:.1f}米 × {height:.1f}米 = {area:.1f}米²"
            else:
                msg = f"Generated {len(points)} drones. Area: {width:.1f}m × {height:.1f}m = {area:.1f}m²"
            self.report({'INFO'}, msg)


class ExportBoxPresetOperator(Operator):
    """Export a box preset configuration to a TXT file."""

    bl_idname = "skybrush.export_box_preset"
    bl_label = "Export Preset"
    bl_options = {'REGISTER'}

    filepath: StringProperty(subtype='FILE_PATH')
    filter_glob: StringProperty(default='*.txt', options={'HIDDEN'})

    def execute(self, context):
        wm = context.window_manager
        orientation = getattr(wm, 'skybrush_box_orientation', "VERTICAL")
        offsets = get_box_offsets(orientation)
        layout = "2x4" if orientation == "VERTICAL" else "4x2"
        export_box_preset(
            self.filepath,
            offsets,
            drones_per_box=8,
            layout=layout,
            name="E4mini",
        )
        self.report({'INFO'}, f"Box preset exported to {self.filepath}")
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class SetDroneCoordOperator(Operator):
    """Set an individual drone's X or Y coordinate within its box slot."""

    bl_idname = "skybrush.set_drone_coord"
    bl_label = "Set Coordinate"
    bl_options = {'REGISTER', 'UNDO'}

    drone_index: IntProperty()
    coord_type: StringProperty()
    value: FloatProperty()

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.layout.prop(self, "value", text=f"{self.coord_type} Coordinate")

    def execute(self, context):
        wm = context.window_manager
        key = f"drone_{self.drone_index}_{self.coord_type}"
        wm[key] = self.value
        return {'FINISHED'}


class ApplyGridLayoutOperator(Operator):
    """Apply the box grid rows/columns to recalculate box and drone counts."""

    bl_idname = "skybrush.apply_grid_layout"
    bl_label = "Apply Grid Layout"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        wm = context.window_manager
        if 'skybrush_grid_rows' in wm and 'skybrush_grid_cols' in wm:
            rows = wm['skybrush_grid_rows']
            cols = wm['skybrush_grid_cols']
            drones_per_box = wm.get('skybrush_drones_per_box', 8)
            boxes = rows * cols
            drones = boxes * drones_per_box
            wm['skybrush_boxes_count'] = boxes
            wm['skybrush_drone_count'] = drones
            self.report({'INFO'}, f"Applied: {rows}×{cols} = {boxes} boxes, {drones} drones")
        else:
            self.report({'WARNING'}, "Please modify rows or columns first")
        return {'FINISHED'}


class ApplyBoxParamsOperator(Operator):
    """Apply custom box parameter edits to the takeoff grid operator."""

    bl_idname = "skybrush.apply_box_params"
    bl_label = "Apply"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        self.report({'INFO'}, "Box parameters applied")
        return {'FINISHED'}
