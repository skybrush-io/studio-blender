from math import ceil, inf

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty
from bpy.types import Context

from sbstudio.errors import SkybrushStudioError
from sbstudio.math.nearest_neighbors import find_nearest_neighbors
from sbstudio.plugin.api import call_api_from_blender_operator, get_api
from sbstudio.plugin.constants import Collections, Formations
from sbstudio.plugin.model.formation import (
    create_formation,
    ensure_formation_consists_of_points,
)
from sbstudio.plugin.model.safety_check import get_proximity_warning_threshold
from sbstudio.plugin.model.storyboard import (
    Storyboard,
    StoryboardEntryPurpose,
    get_storyboard,
)
from sbstudio.plugin.operators.recalculate_transitions import (
    RecalculationTask,
    recalculate_transitions,
)
from sbstudio.plugin.utils.evaluator import create_position_evaluator

from .base import StoryboardOperator

__all__ = ("TakeoffOperator",)


# === Starlight Animator Layer Sequences ===
# Optimized interleave sequences for box takeoff (reduces airflow interference)
INTERLEAVE_8 = [7, 5, 1, 3, 6, 8, 4, 2]
INTERLEAVE_12 = [11, 8, 3, 6, 1, 10, 5, 12, 9, 2, 7, 4]
INTERLEAVE_16 = [13, 10, 5, 2, 9, 14, 1, 6, 15, 12, 7, 4, 11, 16, 3, 8]

# Traditional single-drone array interleave sequences
INTERLEAVE_4 = [3, 1, 4, 2]
INTERLEAVE_9 = [7, 3, 9, 1, 5, 8, 2, 6, 4]


def get_layer_sequence(scheme, spacing_x=1.0, is_traditional=False):
    """Return the interleave sequence for the given scheme."""
    if is_traditional:
        if scheme == "T4":
            return INTERLEAVE_4
        elif scheme == "T9":
            return INTERLEAVE_9
        else:  # AUTO
            return INTERLEAVE_4
    else:
        if scheme == "L8":
            return INTERLEAVE_8
        elif scheme == "L12":
            return INTERLEAVE_12
        elif scheme == "L16":
            return INTERLEAVE_16
        else:  # AUTO
            if spacing_x >= 1.4:
                return INTERLEAVE_8
            elif spacing_x >= 1.0:
                return INTERLEAVE_12
            else:
                return INTERLEAVE_16


def apply_starlight_layering(source, groups, scheme="AUTO", spacing_x=1.0):
    """Apply Starlight Animator's optimized layer sequence to box takeoff groups.

    Args:
        source: List of (x, y, z) positions
        groups: List of group indices (will be replaced)
        scheme: Layer scheme ("AUTO", "L8", "L12", "L16")
        spacing_x: Box spacing in X direction (for AUTO mode)

    Returns:
        Modified groups list with Starlight layering applied
    """
    if not source or not groups:
        return groups

    sequence = get_layer_sequence(scheme, spacing_x, is_traditional=False)
    seq_len = len(sequence)

    new_groups = []
    for i, _ in enumerate(zip(source, groups)):
        pos_in_box = i % 8
        if pos_in_box < seq_len:
            new_layer = sequence[pos_in_box] - 1
        else:
            new_layer = pos_in_box
        new_groups.append(new_layer)

    return new_groups


def apply_traditional_layering(source, groups, scheme="AUTO", rows=8, cols=8):
    """Apply Starlight Animator's optimized layer sequence to traditional single-drone array.

    Args:
        source: List of (x, y, z) positions
        groups: List of group indices (will be replaced)
        scheme: Layer scheme ("AUTO", "T4", "T9")
        rows: Number of rows in the grid
        cols: Number of columns in the grid

    Returns:
        Modified groups list with Starlight layering applied
    """
    if not source or not groups:
        return groups

    sequence = get_layer_sequence(scheme, is_traditional=True)
    seq_len = len(sequence)

    new_groups = []
    for i, _ in enumerate(zip(source, groups)):
        row = i // cols
        col = i % cols
        if seq_len == 4:
            pattern_idx = (row % 2) * 2 + (col % 2)
        elif seq_len == 9:
            pattern_idx = (row % 3) * 3 + (col % 3)
        else:
            pattern_idx = 0

        if pattern_idx < seq_len:
            new_layer = sequence[pattern_idx] - 1
        else:
            new_layer = pattern_idx
        new_groups.append(new_layer)

    return new_groups


def use_custom_spacing_updated(self, context: Context):
    """Called when the use_custom_spacing checkbox is enabled or disabled by the user."""
    if not self.use_custom_spacing:
        self.spacing = get_proximity_warning_threshold(context)


class TakeoffOperator(StoryboardOperator):
    """Blender operator that adds a takeoff transition to the show, starting at
    a given frame.
    """

    bl_idname = "skybrush.takeoff"
    bl_label = "Takeoff"
    bl_description = "Add a takeoff maneuver to all the drones"
    bl_options = {"REGISTER", "UNDO"}

    only_with_valid_storyboard = True

    start_frame = IntProperty(
        name="at Frame", description="Start frame of the takeoff maneuver"
    )

    velocity = FloatProperty(
        name="with Velocity",
        description="Average vertical velocity during the takeoff maneuver",
        default=1.5,
        min=0.1,
        soft_min=0.1,
        soft_max=10,
        unit="VELOCITY",
    )

    altitude = FloatProperty(
        name="to Altitude",
        description=(
            "Altitude to take off to. In case of layered takeoff "
            "the desired takeoff altitude of the lowest layer"
        ),
        default=6,
        soft_min=0,
        soft_max=50,
        unit="LENGTH",
    )

    # TODO(ntamas): test whether it is safe to remove this property without
    # breaking compatibility with older versions

    altitude_is_relative = BoolProperty(
        name="Relative Altitude",
        description=(
            "Specifies whether the takeoff altitude is relative to the current "
            "altitude of the drone. Deprecated; not used any more."
        ),
        default=False,
        options={"HIDDEN"},
    )

    use_custom_spacing = BoolProperty(
        name="Use custom spacing",
        default=False,
        description=(
            "When checked, a custom spacing can be given instead of "
            "the default proximity warning threshold"
        ),
        update=use_custom_spacing_updated,
    )

    spacing = FloatProperty(
        name="Spacing",
        description="Minimum distance between drones during takeoff",
        default=3,
        min=0.1,
        soft_max=50,
        unit="LENGTH",
    )

    altitude_shift = FloatProperty(
        name="Layer height",
        description=(
            "Specifies the difference between altitudes of takeoff layers "
            "for multi-phase takeoffs when multiple drones occupy the same "
            "takeoff slot within safety distance."
        ),
        default=5,
        soft_min=0,
        soft_max=50,
        unit="LENGTH",
    )

    # === Starlight Box Array Layering ===
    use_box_layering = BoolProperty(
        name="Box Array Layering",
        default=False,
        description="Use Starlight Animator's optimized layer sequence for box takeoff (reduces airflow interference)",
    )

    box_layer_scheme = EnumProperty(
        name="Box Layer Scheme",
        description="Layering scheme for box takeoff sequence",
        items=[
            ("AUTO", "Auto", "Automatically select scheme based on box spacing"),
            ("L8", "8-Layer", "8-layer interleave (for spacing ≥1.4m)"),
            ("L12", "12-Layer", "12-layer interleave (for spacing 1.0-1.4m)"),
            ("L16", "16-Layer", "16-layer interleave (for spacing <1.0m)"),
        ],
        default="AUTO",
    )

    # === Starlight Traditional Array Layering ===
    use_traditional_layering = BoolProperty(
        name="Traditional Array Layering",
        default=False,
        description="Use Starlight Animator's optimized layer sequence for traditional single-drone array takeoff",
    )

    traditional_layer_scheme = EnumProperty(
        name="Traditional Layer Scheme",
        description="Layering scheme for traditional array takeoff sequence",
        items=[
            ("AUTO", "Auto", "Automatically select scheme (4-layer)"),
            ("T4", "4-Layer", "4-layer interleave [3,1,4,2]"),
            ("T9", "9-Layer", "9-layer interleave [7,3,9,1,5,8,2,6,4]"),
        ],
        default="AUTO",
    )

    # === Batch Takeoff for Traditional Array ===
    use_batch_takeoff = BoolProperty(
        name="Batch Takeoff",
        default=False,
        description="Enable separate takeoff parameters for traditional array (creates two storyboard entries)",
    )

    batch_start_frame = IntProperty(
        name="Trad Start Frame",
        description=(
            "Start frame for traditional array takeoff. Can be set independently "
            "from the main start frame."
        ),
        default=1,
    )

    batch_velocity = FloatProperty(
        name="with Velocity",
        description="Average vertical velocity for traditional array batch takeoff",
        default=1.5,
        min=0.1,
        soft_min=0.1,
        soft_max=10,
        unit="VELOCITY",
    )

    batch_altitude = FloatProperty(
        name="to Altitude",
        description="Altitude for traditional array batch takeoff",
        default=6,
        soft_min=0,
        soft_max=50,
        unit="LENGTH",
    )

    batch_altitude_shift = FloatProperty(
        name="Layer height",
        description="Layer height for traditional array batch takeoff",
        default=5,
        soft_min=0,
        soft_max=50,
        unit="LENGTH",
    )

    @classmethod
    def poll(cls, context: Context):
        if not super().poll(context):
            return False

        drones = Collections.find_drones(create=False)
        return drones is not None and len(drones.objects) > 0

    def draw(self, context: Context):
        layout = self.layout
        layout.use_property_split = True

        layout.prop(self, "start_frame")
        layout.prop(self, "velocity")
        layout.prop(self, "altitude")
        row = layout.row()
        row.prop(self, "altitude_shift")
        if self.altitude_shift < self.spacing:
            row.alert = True
            row.label(text="", icon="ERROR")
        row = layout.row(heading="Spacing")
        row.prop(self, "use_custom_spacing", text="")
        row = row.row()
        row.prop(self, "spacing", text="")
        row.enabled = self.use_custom_spacing
        if self.spacing < get_proximity_warning_threshold(context):
            row.alert = True
            row.label(text="", icon="ERROR")

        # Box array layering section
        layout.separator()
        layout.prop(self, "use_box_layering")
        if self.use_box_layering:
            box = layout.box()
            box.prop(self, "box_layer_scheme")

        # Traditional array layering section
        layout.separator()
        layout.prop(self, "use_traditional_layering")
        if self.use_traditional_layering:
            box = layout.box()
            box.prop(self, "traditional_layer_scheme")

            # Batch takeoff option (only when traditional layering is enabled)
            box.separator()
            box.prop(self, "use_batch_takeoff")
            if self.use_batch_takeoff:
                batch_box = box.box()
                batch_box.label(text="Traditional Array Batch Takeoff")
                batch_box.prop(self, "batch_start_frame")
                batch_box.prop(self, "batch_velocity")
                batch_box.prop(self, "batch_altitude")
                batch_box.prop(self, "batch_altitude_shift")

    def invoke(self, context: Context, event):
        # The start frame cannot be earlier than the start time of the first
        # formation and must be earlier than the start time of the second
        # formation. Constrain it to the valid range.
        start, end = self._get_valid_range_for_start_frame(context)
        self.start_frame = int(max(min(context.scene.frame_current, end), start))

        if not self.use_custom_spacing:
            self.spacing = get_proximity_warning_threshold(context)

        return context.window_manager.invoke_props_dialog(self)

    def execute_on_storyboard(self, storyboard: Storyboard, entries, context: Context):
        try:
            success = self._run(storyboard, context=context)
        except SkybrushStudioError:
            # These are handled nicely
            success = False
        return {"FINISHED"} if success else {"CANCELLED"}

    def _run(self, storyboard: Storyboard, *, context: Context) -> bool:
        bpy.ops.skybrush.prepare()

        if not self._validate_start_frame(context):
            return False

        drones = Collections.find_drones().objects
        if not drones:
            return False

        # Auto-migration: if no drone has sb_group tag but scene has mixed counts,
        # tag drones automatically for legacy project compatibility
        try:
            from sbstudio.plugin.utils.drone_groups import (
                auto_tag_drones_by_count,
                get_drone_group,
            )
            has_any_tag = any(get_drone_group(d) for d in drones)
            if not has_any_tag:
                scene = context.scene
                box_n = int(scene.get("sb_mixed_box_count", 0))
                trad_n = int(scene.get("sb_mixed_trad_count", 0))
                if box_n > 0 or trad_n > 0:
                    auto_tag_drones_by_count(list(drones), box_n, trad_n)
                    self.report({"INFO"}, f"Auto-tagged drones: {box_n} BOX, {trad_n} TRAD")
        except Exception:
            pass  # Migration is best-effort; don't break takeoff

        if self.use_batch_takeoff and self.use_traditional_layering:
            return self._run_batch_takeoff(storyboard, drones, context)
        else:
            return self._run_single_takeoff(storyboard, drones, context)

    def _run_single_takeoff(self, storyboard: Storyboard, drones, context: Context) -> bool:
        """Standard single takeoff (original logic, enhanced with optional Starlight layering)."""
        source, target, _ = create_helper_formation_for_takeoff_and_landing(
            drones,
            frame=self.start_frame,
            base_altitude=self.altitude,
            layer_height=self.altitude_shift,
            min_distance=self.spacing,
            operator=self,
        )

        # Calculate the Z distance to travel for each drone
        diffs = [t[2] - s[2] for s, t in zip(source, target)]
        if min(diffs) < 0:
            dist = abs(min(diffs))
            self.report(
                {"ERROR"},
                f"At least one drone would have to take off downwards by {dist}m",
            )
            return False

        # Calculate takeoff durations from distances to travel and average velocity
        fps = context.scene.render.fps
        takeoff_durations = [int(ceil((diff / self.velocity) * fps)) for diff in diffs]

        # Ensure drones arrive at the same time
        takeoff_duration = max(takeoff_durations)
        delays = [takeoff_duration - d for d in takeoff_durations]

        # Calculate when the takeoff should end
        end_of_takeoff = self.start_frame + takeoff_duration
        if len(storyboard.entries) > 1:
            assert storyboard.second_entry is not None
            first_frame = storyboard.second_entry.frame_start
            if first_frame < end_of_takeoff:
                self.report(
                    {"ERROR"},
                    f"Takeoff maneuver needs at least {takeoff_duration} frames; "
                    f"there is not enough time after the first entry of the "
                    f"storyboard (frame {first_frame})",
                )
                return False

        entry = storyboard.first_entry
        if entry is None:
            entry = storyboard.add_new_entry(
                formation=create_formation(Formations.TAKEOFF_GRID, source),
                frame_start=self.start_frame,
                duration=0,
                purpose=StoryboardEntryPurpose.TAKEOFF,
                select=False,
                context=context,
            )
        else:
            formation = entry.formation
            if formation is None:
                self.report(
                    {"ERROR"},
                    "First storyboard entry must have an associated formation",
                )
            ensure_formation_consists_of_points(formation, source)

        # Add a new storyboard entry with the targets of the takeoff
        entry = storyboard.add_new_entry(
            formation=create_formation(Formations.TAKEOFF, target),
            frame_start=end_of_takeoff,
            duration=0,
            purpose=StoryboardEntryPurpose.TAKEOFF,
            select=True,
            context=context,
        )
        assert entry is not None
        entry.transition_type = "MANUAL"
        entry.transition_velocity_profile = "LINEAR"

        # Set up the custom departure delays for the drones
        if delays and max(delays) > 0:
            entry.schedule_overrides_enabled = True
            for index, delay in enumerate(delays):
                if delay > 0:
                    override = entry.add_new_schedule_override()
                    override.index = index
                    override.pre_delay = delay

        # Recalculate the transitions leading from and to the target formation
        tasks = [
            RecalculationTask.for_entry_by_index(storyboard.entries, 0),
            RecalculationTask.for_entry_by_index(storyboard.entries, 1),
        ]
        if len(storyboard.entries) > 2:
            tasks.append(RecalculationTask.for_entry_by_index(storyboard.entries, 2))

        start_of_scene = min(context.scene.frame_start, storyboard.frame_start)
        try:
            with call_api_from_blender_operator(self, "transition planner"):
                recalculate_transitions(tasks, start_of_scene=start_of_scene)
        except Exception:
            return False

        return True

    def _run_batch_takeoff(self, storyboard: Storyboard, drones, context: Context) -> bool:
        """Batch takeoff for mixed mode: two independent storyboard entries.

        Creates "Takeoff (Box)" and "Takeoff (Trad)" entries, each with
        limit_to_group set so only its respective drones participate.
        """
        scene = context.scene
        box_count = int(scene.get("sb_mixed_box_count", 0))
        trad_count = int(scene.get("sb_mixed_trad_count", 0))
        n = len(drones)

        if box_count <= 0 or trad_count <= 0 or (box_count + trad_count) != n:
            self.report(
                {"WARNING"},
                f"Batch takeoff requires mixed mode takeoff grid "
                f"(box={box_count}, trad={trad_count}, total={n}). "
                f"Falling back to single takeoff.",
            )
            return self._run_single_takeoff(storyboard, drones, context)

        with create_position_evaluator() as get_positions_of:
            source = list(get_positions_of(drones, frame=self.start_frame))

        box_source = source[:box_count]
        trad_source = source[box_count:]

        box_target = self._compute_targets(
            box_source,
            base_altitude=self.altitude,
            layer_height=self.altitude_shift,
            use_layering=self.use_box_layering,
            scheme=self.box_layer_scheme,
            spacing_x=self.spacing,
            is_traditional=False,
        )
        trad_target = self._compute_targets(
            trad_source,
            base_altitude=self.batch_altitude,
            layer_height=self.batch_altitude_shift,
            use_layering=self.use_traditional_layering,
            scheme=self.traditional_layer_scheme,
            spacing_x=1.0,
            is_traditional=True,
        )

        fps = context.scene.render.fps

        box_diffs = [t[2] - s[2] for s, t in zip(box_source, box_target)]
        if box_diffs and min(box_diffs) < 0:
            self.report({"ERROR"}, f"Box: drone would take off downwards by {abs(min(box_diffs))}m")
            return False
        box_durations = [int(ceil((d / self.velocity) * fps)) if d > 0 else 0 for d in box_diffs]
        box_takeoff_dur = (max(box_durations) if box_durations else 1) + 1
        end_of_box_takeoff = self.start_frame + box_takeoff_dur
        box_delays = [max(0, box_takeoff_dur - d - 1) for d in box_durations]

        trad_diffs = [t[2] - s[2] for s, t in zip(trad_source, trad_target)]
        if trad_diffs and min(trad_diffs) < 0:
            self.report({"ERROR"}, f"Trad: drone would take off downwards by {abs(min(trad_diffs))}m")
            return False
        trad_durations = [int(ceil((d / self.batch_velocity) * fps)) if d > 0 else 0 for d in trad_diffs]
        trad_takeoff_dur = (max(trad_durations) if trad_durations else 1) + 1
        end_of_trad_takeoff = self.batch_start_frame + trad_takeoff_dur
        trad_delays = [max(0, trad_takeoff_dur - d - 1) for d in trad_durations]

        # Ensure takeoff grid entry exists
        entry = storyboard.first_entry
        if entry is None:
            entry = storyboard.add_new_entry(
                formation=create_formation(Formations.TAKEOFF_GRID, source),
                frame_start=min(self.start_frame, self.batch_start_frame),
                duration=0,
                purpose=StoryboardEntryPurpose.TAKEOFF,
                select=False,
                context=context,
            )
        else:
            formation = entry.formation
            if formation is None:
                self.report({"ERROR"}, "First storyboard entry must have an associated formation")
                return False
            ensure_formation_consists_of_points(formation, source)

        # Create Box and Trad takeoff entries with GROUP-ONLY formations.
        # Each formation contains ONLY its own group's target points
        # (box_count or trad_count markers). The non-participating group's
        # drones are filtered out by ``entry.limit_to_group`` in the
        # transition recalculation logic, so they get no constraint for this
        # entry and simply keep their position from the previous entry.
        #
        # Combined with ``transition_type = "MANUAL"`` and the per-entry
        # group filter, this guarantees that the i-th participating drone
        # maps to the i-th marker — i.e. drone X goes to its own target
        # position regardless of how the optimizer would otherwise re-shuffle
        # things based on geometric distances.
        box_formation = create_formation("Takeoff (Box)", list(box_target))
        storyboard.add_new_entry(
            formation=box_formation,
            frame_start=end_of_box_takeoff,
            duration=0,
            purpose=StoryboardEntryPurpose.TAKEOFF,
            select=False,
            context=context,
        )

        trad_formation = create_formation("Takeoff (Trad)", list(trad_target))
        storyboard.add_new_entry(
            formation=trad_formation,
            frame_start=end_of_trad_takeoff,
            duration=0,
            purpose=StoryboardEntryPurpose.TAKEOFF,
            select=True,
            context=context,
        )

        # Re-fetch entries via stable formation references
        entries_list = list(storyboard.entries)
        box_entry = next((e for e in entries_list if e.formation == box_formation), None)
        trad_entry = next((e for e in entries_list if e.formation == trad_formation), None)
        assert box_entry is not None and trad_entry is not None

        # MANUAL transitions: the i-th marker of the source formation is
        # mapped to the i-th marker of the target formation.  We constructed
        # both formations so that index i corresponds to the i-th drone
        # globally (first box_count = box drones, remainder = trad drones),
        # so MANUAL is exactly what we need.  AUTO would let the optimizer
        # swap drones across groups when group footprints overlap or when
        # delays make swapped paths look "shorter" by the optimizer's metric.
        box_entry.transition_type = "MANUAL"
        box_entry.limit_to_group = "BOX"
        trad_entry.transition_type = "MANUAL"
        trad_entry.limit_to_group = "TRAD"

        # Only the earlier takeoff entry keeps TAKEOFF purpose
        if box_entry.frame_start <= trad_entry.frame_start:
            trad_entry.purpose = StoryboardEntryPurpose.UNSPECIFIED.name
        else:
            box_entry.purpose = StoryboardEntryPurpose.UNSPECIFIED.name

        # Apply schedule overrides
        box_pos = entries_list.index(box_entry)
        trad_pos = entries_list.index(trad_entry)
        box_pred_end = entries_list[box_pos - 1].frame_end if box_pos > 0 else (context.scene.frame_start or 0)
        trad_pred_end = entries_list[trad_pos - 1].frame_end if trad_pos > 0 else (context.scene.frame_start or 0)
        box_gap = max(0, self.start_frame - box_pred_end)
        trad_gap = max(0, self.batch_start_frame - trad_pred_end)

        box_total_delays = [box_gap + d for d in box_delays]
        if box_total_delays and max(box_total_delays) > 0:
            box_entry.schedule_overrides_enabled = True
            for global_idx, total in enumerate(box_total_delays):
                if total > 0:
                    override = box_entry.add_new_schedule_override()
                    override.index = global_idx
                    override.pre_delay = total

        trad_total_delays = [trad_gap + d for d in trad_delays]
        if trad_total_delays and max(trad_total_delays) > 0:
            trad_entry.schedule_overrides_enabled = True
            for local_idx, total in enumerate(trad_total_delays):
                if total > 0:
                    override = trad_entry.add_new_schedule_override()
                    override.index = box_count + local_idx
                    override.pre_delay = total

        # Recalculate all transitions
        tasks = [
            RecalculationTask.for_entry_by_index(storyboard.entries, i)
            for i in range(len(storyboard.entries))
        ]
        start_of_scene = min(context.scene.frame_start, storyboard.frame_start)
        try:
            with call_api_from_blender_operator(self, "transition planner"):
                recalculate_transitions(tasks, start_of_scene=start_of_scene)
        except Exception:
            return False

        self.report(
            {"INFO"},
            f"Box: {self.start_frame}->{end_of_box_takeoff} ({box_count} drones); "
            f"Trad: {self.batch_start_frame}->{end_of_trad_takeoff} ({trad_count} drones)",
        )
        return True

    def _compute_targets(self, source, *, base_altitude, layer_height,
                         use_layering, scheme, spacing_x, is_traditional):
        """Compute target positions for a group of drones, applying Starlight layering if enabled."""
        n = len(source)
        if n == 0:
            return []

        if use_layering:
            groups = [0] * n
            if is_traditional:
                cols = max(1, int(n ** 0.5))
                rows = (n + cols - 1) // cols
                groups = apply_traditional_layering(source, groups, scheme=scheme, rows=rows, cols=cols)
            else:
                groups = apply_starlight_layering(source, groups, scheme=scheme, spacing_x=spacing_x)
        else:
            min_distance = self.spacing
            if n >= 2:
                _, _, dist = find_nearest_neighbors(source)
            else:
                dist = float('inf')
            if dist < min_distance and n >= 2:
                with call_api_from_blender_operator(self, "point decomposition") as api:
                    groups = api.decompose_points(source, min_distance=min_distance, method="greedy")
            else:
                groups = [0] * n

        num_groups = max(groups) + 1 if groups else 0
        target = [
            (x, y, base_altitude + (num_groups - g - 1) * layer_height)
            for (x, y, _), g in zip(source, groups)
        ]
        return target

    def _get_valid_range_for_start_frame(self, context: Context) -> tuple[float, float]:
        """Returns the interval that must contain the start frame of the takeoff
        operation.

        The returned range is closed from the left and open from the right.
        """
        # Note: we assume here that the first entry is the takeoff grid on ground
        storyboard = get_storyboard(context=context)
        if len(storyboard.entries) <= 0:
            # Storyboard is empty
            return -inf, inf
        elif len(storyboard.entries) == 1:
            # Storyboard has a takeoff grid only
            assert storyboard.first_entry is not None
            return storyboard.first_entry.frame_end, inf
        else:
            # Storyboard has both a takeoff grid and an existing takeoff
            # formation
            assert storyboard.first_entry is not None
            assert storyboard.second_entry is not None
            return storyboard.first_entry.frame_end, storyboard.second_entry.frame_start

    def _validate_start_frame(self, context: Context) -> bool:
        """Returns whether the takeoff time chosen by the user is valid."""
        start, end = self._get_valid_range_for_start_frame(context)
        if self.start_frame < start:
            self.report(
                {"ERROR"},
                (
                    f"Takeoff maneuver must start after the first (takeoff "
                    f"grid) entry of the storyboard (frame {start})"
                ),
            )
            return False

        if self.start_frame >= end:
            self.report(
                {"ERROR"},
                (
                    f"Takeoff maneuver must start before the second "
                    f"entry of the storyboard (frame {end})"
                ),
            )
            return False

        return True


def create_helper_formation_for_takeoff_and_landing(
    drones,
    *,
    frame: int,
    base_altitude: float,
    layer_height: float,
    min_distance: float,
    flatten_source: bool = False,
    operator=None,
):
    """Creates a layer helper formation for takeoff and landing where the drones
    are placed directly above their positions at the given frame, at the given
    base altitude plus an altitude shift per layer to ensure minimum distance
    constraints.

    Returns:
        the source points, the target points, and the assignment of target
        points to layers (layer 0 being at the lowest altitude)
    """
    # Evaluate the initial positions of the drones
    with create_position_evaluator() as get_positions_of:
        source = get_positions_of(drones, frame=frame)
    # Flatten source if needed (e.g if called from a show
    # starting with a floating grid and not from ground)
    if flatten_source:
        min_alt = min(p[2] for p in source)
        source = [(p[0], p[1], min_alt) for p in source]

    # Check if Starlight layering is requested via the operator
    use_box_layering = getattr(operator, "use_box_layering", False) if operator else False
    use_trad_layering = getattr(operator, "use_traditional_layering", False) if operator else False

    if use_box_layering or use_trad_layering:
        box_scheme = getattr(operator, "box_layer_scheme", "AUTO") if operator else "AUTO"
        trad_scheme = getattr(operator, "traditional_layer_scheme", "AUTO") if operator else "AUTO"
        spacing_x = getattr(operator, "spacing", 1.0) if operator else 1.0

        # Detect mixed mode from scene metadata
        try:
            scene = bpy.context.scene
            box_count = int(scene.get("sb_mixed_box_count", 0))
            trad_count = int(scene.get("sb_mixed_trad_count", 0))
        except Exception:
            box_count = trad_count = 0

        n = len(source)
        is_mixed = box_count > 0 and trad_count > 0 and (box_count + trad_count) == n

        if is_mixed:
            box_src = source[:box_count]
            trad_src = source[box_count:]
            box_groups = [0] * box_count
            trad_groups = [0] * trad_count

            if use_box_layering:
                box_groups = apply_starlight_layering(box_src, box_groups, scheme=box_scheme, spacing_x=spacing_x)
            if use_trad_layering:
                cols = max(1, int(trad_count ** 0.5))
                rows = (trad_count + cols - 1) // cols
                trad_groups = apply_traditional_layering(trad_src, trad_groups, scheme=trad_scheme, rows=rows, cols=cols)

            box_num = (max(box_groups) + 1) if box_groups else 0
            trad_num = (max(trad_groups) + 1) if trad_groups else 0
            box_target = [
                (x, y, base_altitude + (box_num - g - 1) * layer_height)
                for (x, y, _), g in zip(box_src, box_groups)
            ]
            trad_target = [
                (x, y, base_altitude + (trad_num - g - 1) * layer_height)
                for (x, y, _), g in zip(trad_src, trad_groups)
            ]
            target = list(box_target) + list(trad_target)
            return source, target, list(box_groups) + list(trad_groups)
        else:
            groups = [0] * n
            if use_box_layering:
                groups = apply_starlight_layering(source, groups, scheme=box_scheme, spacing_x=spacing_x)
            elif use_trad_layering:
                cols = max(1, int(n ** 0.5))
                rows = (n + cols - 1) // cols
                groups = apply_traditional_layering(source, groups, scheme=trad_scheme, rows=rows, cols=cols)
    else:
        # Original Studio logic: use decompose_points
        _, _, dist = find_nearest_neighbors(source)
        if dist < min_distance:
            if operator is not None:
                with call_api_from_blender_operator(operator, "point decomposition") as api:
                    groups = api.decompose_points(
                        source, min_distance=min_distance, method="greedy"
                    )
            else:
                groups = get_api().decompose_points(
                    source, min_distance=min_distance, method="greedy"
                )
        else:
            # We can save an API call here
            groups = [0] * len(source)

    num_groups = max(groups) + 1 if groups else 0

    # Prepare the points of the target formation to take off to or to return to
    target = [
        (x, y, base_altitude + (num_groups - group - 1) * layer_height)
        for (x, y, _), group in zip(source, groups)
    ]

    return source, target, groups
