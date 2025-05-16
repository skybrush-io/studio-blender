"""Blender operators registered by Skybrush Studio for Blender."""

from .add_markers_from_qr_code import AddMarkersFromQRCodeOperator
from .add_markers_from_static_csv import AddMarkersFromStaticCSVOperator
from .add_markers_from_svg import AddMarkersFromSVGOperator
from .add_markers_from_zipped_csv import AddMarkersFromZippedCSVOperator
from .add_markers_from_zipped_dss import AddMarkersFromZippedDSSOperator
from .append_formation_to_storyboard import AppendFormationToStoryboardOperator
from .apply_color import ApplyColorsToSelectedDronesOperator
from .create_formation import CreateFormationOperator
from .create_light_effect import CreateLightEffectOperator
from .create_new_schedule_override_entry import CreateNewScheduleOverrideEntryOperator
from .create_new_storyboard_entry import CreateNewStoryboardEntryOperator
from .create_takeoff_grid import CreateTakeoffGridOperator
from .detach_materials_from_template import DetachMaterialsFromDroneTemplateOperator
from .duplicate_light_effect import DuplicateLightEffectOperator
from .export_to_csv import SkybrushCSVExportOperator
from .export_to_dac import DACExportOperator
from .export_to_ddsf import DDSFExportOperator
from .export_to_dss import DSSPathExportOperator, DSSPath3ExportOperator
from .export_to_evsky import EVSKYExportOperator
from .export_to_drotek import DrotekExportOperator
from .export_to_litebee import LitebeeExportOperator
from .export_to_skyc import SkybrushExportOperator
from .export_to_vviz import VVIZExportOperator
from .export_to_pdf import SkybrushPDFExportOperator
from .fix_constraint_ordering import FixConstraintOrderingOperator
from .get_formation_stats import GetFormationStatisticsOperator
from .land import LandOperator
from .move_light_effect import (
    MoveLightEffectDownOperator,
    MoveLightEffectUpOperator,
)
from .move_storyboard_entry import (
    MoveStoryboardEntryDownOperator,
    MoveStoryboardEntryUpOperator,
)
from .prepare import PrepareSceneOperator
from .recalculate_transitions import RecalculateTransitionsOperator
from .refresh_file_formats import RefreshFileFormatsOperator
from .remove_formation import RemoveFormationOperator
from .remove_light_effect import RemoveLightEffectOperator
from .remove_schedule_override_entry import RemoveScheduleOverrideEntryOperator
from .remove_storyboard_entry import RemoveStoryboardEntryOperator
from .reorder_formation_markers import ReorderFormationMarkersOperator
from .return_to_home import ReturnToHomeOperator
from .run_full_proximity_check import RunFullProximityCheckOperator
from .select_formation import SelectFormationOperator, DeselectFormationOperator
from .select_storyboard_entry import SelectStoryboardEntryForCurrentFrameOperator
from .set_server_url import SetServerURLOperator
from .swap_colors import SwapColorsInLEDControlPanelOperator
from .takeoff import TakeoffOperator
from .update_formation import UpdateFormationOperator
from .update_time_markers_from_storyboard import UpdateTimeMarkersFromStoryboardOperator
from .update_frame_range_from_storyboard import UpdateFrameRangeFromStoryboardOperator
from .use_vgroup_for_formation import UseSelectedVertexGroupForFormationOperator
from .validate_trajectories import ValidateTrajectoriesOperator

__all__ = (
    "AddMarkersFromQRCodeOperator",
    "AddMarkersFromStaticCSVOperator",
    "AddMarkersFromSVGOperator",
    "AddMarkersFromZippedCSVOperator",
    "AppendFormationToStoryboardOperator",
    "ApplyColorsToSelectedDronesOperator",
    "CreateFormationOperator",
    "CreateLightEffectOperator",
    "CreateNewScheduleOverrideEntryOperator",
    "CreateNewStoryboardEntryOperator",
    "CreateTakeoffGridOperator",
    "DACExportOperator",
    "DDSFExportOperator",
    "DeselectFormationOperator",
    "DetachMaterialsFromDroneTemplateOperator",
    "DrotekExportOperator",
    "DSSPath3ExportOperator",
    "DSSPathExportOperator",
    "DuplicateLightEffectOperator",
    "EVSKYExportOperator",
    "FixConstraintOrderingOperator",
    "GetFormationStatisticsOperator",
    "LandOperator",
    "LitebeeExportOperator",
    "MoveLightEffectDownOperator",
    "MoveLightEffectUpOperator",
    "MoveStoryboardEntryDownOperator",
    "MoveStoryboardEntryUpOperator",
    "PrepareSceneOperator",
    "RecalculateTransitionsOperator",
    "RefreshFileFormatsOperator",
    "RemoveFormationOperator",
    "RemoveLightEffectOperator",
    "RemoveScheduleOverrideEntryOperator",
    "RemoveStoryboardEntryOperator",
    "ReorderFormationMarkersOperator",
    "ReturnToHomeOperator",
    "RunFullProximityCheckOperator",
    "SelectFormationOperator",
    "SelectStoryboardEntryForCurrentFrameOperator",
    "SetServerURLOperator",
    "SkybrushCSVExportOperator",
    "SkybrushExportOperator",
    "SkybrushPDFExportOperator",
    "SwapColorsInLEDControlPanelOperator",
    "TakeoffOperator",
    "UpdateFormationOperator",
    "UpdateFrameRangeFromStoryboardOperator",
    "UpdateTimeMarkersFromStoryboardOperator",
    "UseSelectedVertexGroupForFormationOperator",
    "ValidateTrajectoriesOperator",
    "VVIZExportOperator",
)
