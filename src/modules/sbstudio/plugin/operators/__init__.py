"""Blender operators registered by the Skybrush Studio plugin."""

from .apply_color import ApplyColorsToSelectedDronesOperator
from .create_formation import CreateFormationOperator
from .create_new_storyboard_entry import CreateNewStoryboardEntryOperator
from .create_takeoff_grid import CreateTakeoffGridOperator
from .detach_materials_from_template import DetachMaterialsFromDroneTemplateOperator
from .prepare import PrepareSceneOperator
from .recalculate_transitions import RecalculateTransitionsOperator
from .remove_storyboard_entry import RemoveStoryboardEntryOperator
from .swap_colors import SwapColorsInLEDControlPanelOperator

__all__ = (
    "ApplyColorsToSelectedDronesOperator",
    "CreateFormationOperator",
    "CreateNewStoryboardEntryOperator",
    "CreateTakeoffGridOperator",
    "DetachMaterialsFromDroneTemplateOperator",
    "PrepareSceneOperator",
    "RecalculateTransitionsOperator",
    "RemoveStoryboardEntryOperator",
    "SwapColorsInLEDControlPanelOperator",
)