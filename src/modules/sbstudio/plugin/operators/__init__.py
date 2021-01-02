"""Blender operators registered by the Skybrush Studio plugin."""

from .append_formation_to_storyboard import AppendFormationToStoryboardOperator
from .apply_color import ApplyColorsToSelectedDronesOperator
from .create_formation import CreateFormationOperator
from .create_new_storyboard_entry import CreateNewStoryboardEntryOperator
from .create_takeoff_grid import CreateTakeoffGridOperator
from .detach_materials_from_template import DetachMaterialsFromDroneTemplateOperator
from .export_to_skyc import SkybrushExportOperator
from .fix_constraint_ordering import FixConstraintOrderingOperator
from .move_storyboard_entry import (
    MoveStoryboardEntryDownOperator,
    MoveStoryboardEntryUpOperator,
)
from .prepare import PrepareSceneOperator
from .recalculate_transitions import RecalculateTransitionsOperator
from .remove_formation import RemoveFormationOperator
from .remove_storyboard_entry import RemoveStoryboardEntryOperator
from .select_formation import SelectFormationOperator, DeselectFormationOperator
from .select_storyboard_entry import SelectStoryboardEntryForCurrentFrameOperator
from .swap_colors import SwapColorsInLEDControlPanelOperator
from .update_formation import UpdateFormationOperator
from .validate_trajectories import ValidateTrajectoriesOperator

__all__ = (
    "AppendFormationToStoryboardOperator",
    "ApplyColorsToSelectedDronesOperator",
    "CreateFormationOperator",
    "CreateNewStoryboardEntryOperator",
    "CreateTakeoffGridOperator",
    "DeselectFormationOperator",
    "DetachMaterialsFromDroneTemplateOperator",
    "FixConstraintOrderingOperator",
    "MoveStoryboardEntryDownOperator",
    "MoveStoryboardEntryUpOperator",
    "PrepareSceneOperator",
    "RecalculateTransitionsOperator",
    "RemoveFormationOperator",
    "RemoveStoryboardEntryOperator",
    "SelectFormationOperator",
    "SelectStoryboardEntryForCurrentFrameOperator",
    "SkybrushExportOperator",
    "SwapColorsInLEDControlPanelOperator",
    "UpdateFormationOperator",
    "ValidateTrajectoriesOperator",
)
