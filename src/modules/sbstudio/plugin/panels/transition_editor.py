from bpy.types import Panel

from sbstudio.plugin.model.storyboard import get_storyboard, Storyboard, StoryboardEntry
from sbstudio.plugin.operators import (
    CreateNewScheduleOverrideEntryOperator,
    RecalculateTransitionsOperator,
    RemoveScheduleOverrideEntryOperator,
)


def format_transition_duration(duration: int) -> str:
    """Formats the duration of a transition in a nice human-readable manner."""
    if duration > 1:
        return f"{duration} frames"
    elif duration > 0:
        return "Single-frame transition"
    else:
        return "Zero-frame transition"


class TransitionEditorBase(Panel):
    """Base class for transition editors."""

    bl_space_type = "VIEW_3D"

    # Prevent the panel from appearing on its own in "Misc"
    bl_region_type = "WINDOW"
    bl_options = {"INSTANCED"}

    @classmethod
    def _get_entry(cls, storyboard: Storyboard) -> StoryboardEntry | None:
        """Returns the entry that the transition editor will edit."""
        return None

    @classmethod
    def poll(cls, context) -> bool:
        storyboard = get_storyboard(context=context)
        if storyboard is not None:
            return cls._get_entry(storyboard) is not None
        else:
            return False

    @classmethod
    def _get_info_labels(
        cls, storyboard: Storyboard, entry: StoryboardEntry
    ) -> list[str]:
        return []

    @classmethod
    def _get_recalculation_scope(cls) -> str:
        return "ALL"

    def draw(self, context):
        storyboard = get_storyboard(context=context)
        entry = self._get_entry(storyboard)
        if entry is None:
            return

        layout = self.layout

        for label in self._get_info_labels(storyboard, entry):
            layout.label(text=label)

        layout.prop(entry, "transition_type")
        layout.prop(entry, "transition_schedule")
        if entry.is_staggered:
            layout.prop(entry, "pre_delay_per_drone_in_frames")
            layout.prop(entry, "post_delay_per_drone_in_frames")

        layout.prop(entry, "schedule_overrides_enabled", text="Schedule overrides")
        if entry.schedule_overrides_enabled:
            row = layout.row()

            col = row.column()
            col.template_list(
                "SKYBRUSH_UL_scheduleoverridelist",
                self.bl_idname,
                entry,
                "schedule_overrides",
                entry,
                "active_schedule_override_entry_index",
                maxrows=6,
                sort_lock=True,
            )

            col = row.column(align=True)
            col.operator(
                CreateNewScheduleOverrideEntryOperator.bl_idname, icon="ADD", text=""
            )
            col.operator(
                RemoveScheduleOverrideEntryOperator.bl_idname, icon="REMOVE", text=""
            )

            schedule_override = entry.active_schedule_override_entry
            if schedule_override:
                row = layout.row()
                row.prop(schedule_override, "index", text="Marker index")

                row = layout.row()
                row.prop(schedule_override, "pre_delay", text="Dep")
                row.prop(schedule_override, "post_delay", text="Arr")

            layout.separator()

        layout.prop(entry, "is_locked")

        props = layout.operator(
            RecalculateTransitionsOperator.bl_idname, text="Recalculate"
        )
        props.scope = self._get_recalculation_scope()


class TransitionEditorIntoCurrentFormation(TransitionEditorBase):
    """Edits the transition into the currently selected formation."""

    bl_idname = "OBJECT_PT_skybrush_transition_editor_pre"
    bl_label = "Transition from previous"
    bl_description = "Edits the transition into the currently selected formation"

    @classmethod
    def _get_entry(cls, storyboard: Storyboard) -> StoryboardEntry | None:
        entry = storyboard.active_entry
        return entry if entry != storyboard.first_entry else None

    @classmethod
    def _get_info_labels(
        cls, storyboard: Storyboard, entry: StoryboardEntry
    ) -> list[str]:
        duration = storyboard.get_transition_duration_into_current_entry()
        return [format_transition_duration(duration)]

    @classmethod
    def _get_recalculation_scope(cls) -> str:
        return "TO_SELECTED"


class TransitionEditorFromCurrentFormation(TransitionEditorBase):
    """Edits the transition to the formation that follows the currently selected
    formation.
    """

    bl_idname = "OBJECT_PT_skybrush_transition_editor_post"
    bl_label = "Transition to next"
    bl_description = "Edits the transition to the formation that follows the currently selected formation"

    @classmethod
    def _get_entry(cls, storyboard: Storyboard) -> StoryboardEntry | None:
        return storyboard.entry_after_active_entry if storyboard else None

    @classmethod
    def _get_info_labels(
        cls, storyboard: Storyboard, entry: StoryboardEntry
    ) -> list[str]:
        duration = storyboard.get_transition_duration_from_current_entry()
        return [format_transition_duration(duration)]

    @classmethod
    def _get_recalculation_scope(cls) -> str:
        return "FROM_SELECTED"
