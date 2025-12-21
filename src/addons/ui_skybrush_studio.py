bl_info = {
    "name": "Skybrush Studio",
    "author": "CollMot Robotics Ltd.",
    "description": "Extends Blender with UI components for drone show design",
    "version": (4, 0, 2),
    "blender": (4, 4, 0),
    "category": "Interface",
    "doc_url": "https://doc.collmot.com/public/skybrush-studio-for-blender/latest/",
    "tracker_url": "https://github.com/skybrush-io/studio-blender/issues",
}

__license__ = "GPLv3"

# BLENDER ADD-ON INFO ENDS HERE ### DO NOT REMOVE THIS LINE #################

#############################################################################
# imports needed to set up the Python path properly

import sys

from bpy.props import PointerProperty
from bpy.types import Object, Scene
from functools import partial
from pathlib import Path


#############################################################################
# Note: This code needs to be harmonized with the plugin installer to have
# the same target directory for all add-on specific dependencies.

candidates = [
    Path(sys.modules[__name__].__file__).parent,
    Path(sys.modules[__name__].__file__).parent.parent,
]
for candidate in candidates:
    path = (Path(candidate) / "vendor" / "skybrush").resolve()
    if path.exists():
        sys.path.insert(0, str(path))
        break


#############################################################################
# imports needed by the addon

from sbstudio.i18n.translations import translations_dict
from sbstudio.plugin.lists import (
    SKYBRUSH_UL_lightfxlist,
    SKYBRUSH_UL_scheduleoverridelist,
)
from sbstudio.plugin.menus import GenerateMarkersMenu
from sbstudio.plugin.model import (
    DroneShowAddonFileSpecificSettings,
    DroneShowAddonGlobalSettings,
    DroneShowAddonProperties,
    DroneShowAddonObjectProperties,
    FormationsPanelProperties,
    LEDControlPanelProperties,
    LightEffect,
    LightEffectCollection,
    ColorFunctionProperties,
    PyroControlPanelProperties,
    SafetyCheckProperties,
    ScheduleOverride,
    StoryboardEntry,
    StoryboardEntryOrTransition,
    Storyboard,
    get_formation_order_overlay,
    get_safety_check_overlay,
)
from sbstudio.plugin.operators import (
    AddMarkersFromStaticCSVOperator,
    AddMarkersFromSVGOperator,
    AddMarkersFromZippedCSVOperator,
    AddMarkersFromZippedDSSOperator,
    AppendFormationToStoryboardOperator,
    ApplyColorsToSelectedDronesOperator,
    CreateFormationOperator,
    CreateNewScheduleOverrideEntryOperator,
    CreateNewStoryboardEntryOperator,
    CreateLightEffectOperator,
    CreateTakeoffGridOperator,
    DACExportOperator,
    DeselectFormationOperator,
    DetachMaterialsFromDroneTemplateOperator,
    DDSFExportOperator,
    DrotekExportOperator,
    DSSPathExportOperator,
    DSSPath3ExportOperator,
    EVSKYExportOperator,
    ExportLightEffectsOperator,
    ImportLightEffectsOperator,
    DuplicateLightEffectOperator,
    FixConstraintOrderingOperator,
    AddMarkersFromQRCodeOperator,
    GetFormationStatisticsOperator,
    LandOperator,
    LitebeeExportOperator,
    MoveLightEffectDownOperator,
    MoveLightEffectUpOperator,
    MoveStoryboardEntryDownOperator,
    MoveStoryboardEntryUpOperator,
    PrepareSceneOperator,
    RecalculateTransitionsOperator,
    RefreshFileFormatsOperator,
    RemoveFormationOperator,
    RemoveLightEffectOperator,
    RemoveScheduleOverrideEntryOperator,
    RemoveStoryboardEntryOperator,
    ReorderFormationMarkersOperator,
    ReturnToHomeOperator,
    RunFullProximityCheckOperator,
    SelectFormationOperator,
    SelectStoryboardEntryForCurrentFrameOperator,
    SetLightEffectEndFrameOperator,
    SetLightEffectStartFrameOperator,
    SetStoryboardEntryEndFrameOperator,
    SetStoryboardEntryStartFrameOperator,
    SetServerURLOperator,
    SkybrushExportOperator,
    SkybrushCSVExportOperator,
    SkybrushPDFExportOperator,
    SkybrushSKYCAndPDFExportOperator,
    SwapColorsInLEDControlPanelOperator,
    TakeoffOperator,
    TriggerPyroOnSelectedDronesOperator,
    UpdateFormationOperator,
    UpdateFrameRangeFromStoryboardOperator,
    UpdateTimeMarkersFromStoryboardOperator,
    UseSelectedVertexGroupForFormationOperator,
    UseSharedMaterialForAllDronesMigrationOperator,
    ValidateTrajectoriesOperator,
    VVIZExportOperator,
)
from sbstudio.plugin.panels import (
    DroneShowAddonObjectPropertiesPanel,
    ExportPanel,
    FormationsPanel,
    StoryboardEditor,
    LEDControlPanel,
    LightEffectsPanel,
    PyroControlPanel,
    SafetyCheckPanel,
    ShowPanel,
    SwarmPanel,
    TransitionEditorFromCurrentFormation,
    TransitionEditorIntoCurrentFormation,
)
from sbstudio.plugin.plugin_helpers import (
    register_header,
    register_list,
    register_menu,
    register_operator,
    register_panel,
    register_translations,
    register_type,
    unregister_header,
    unregister_list,
    unregister_menu,
    unregister_operator,
    unregister_panel,
    unregister_translations,
    unregister_type,
)
from sbstudio.plugin.state import (
    register as register_state,
    unregister as unregister_state,
)
from sbstudio.plugin.tasks import (
    InitializationTask,
    InvalidatePixelCacheTask,
    PyroEffectsTask,
    SafetyCheckTask,
    UpdateLightEffectsTask,
)


#: Custom types in this addon
types = (
    FormationsPanelProperties,
    ColorFunctionProperties,
    ScheduleOverride,
    StoryboardEntry,
    StoryboardEntryOrTransition,
    Storyboard,
    LightEffect,
    LightEffectCollection,
    LEDControlPanelProperties,
    PyroControlPanelProperties,
    SafetyCheckProperties,
    DroneShowAddonFileSpecificSettings,
    DroneShowAddonGlobalSettings,
    DroneShowAddonProperties,
    DroneShowAddonObjectProperties,
)

#: Operators in this addon; operators that require other operators must come
#: later in the list than their dependencies
operators = (
    PrepareSceneOperator,
    CreateFormationOperator,
    SelectFormationOperator,
    DeselectFormationOperator,
    UpdateFormationOperator,
    ReorderFormationMarkersOperator,
    RemoveFormationOperator,
    CreateNewStoryboardEntryOperator,
    AppendFormationToStoryboardOperator,
    MoveStoryboardEntryDownOperator,
    MoveStoryboardEntryUpOperator,
    SelectStoryboardEntryForCurrentFrameOperator,
    RemoveStoryboardEntryOperator,
    SetStoryboardEntryEndFrameOperator,
    SetStoryboardEntryStartFrameOperator,
    CreateNewScheduleOverrideEntryOperator,
    RemoveScheduleOverrideEntryOperator,
    UpdateFrameRangeFromStoryboardOperator,
    UpdateTimeMarkersFromStoryboardOperator,
    CreateLightEffectOperator,
    DuplicateLightEffectOperator,
    ExportLightEffectsOperator,
    ImportLightEffectsOperator,
    MoveLightEffectDownOperator,
    MoveLightEffectUpOperator,
    RemoveLightEffectOperator,
    SetLightEffectEndFrameOperator,
    SetLightEffectStartFrameOperator,
    CreateTakeoffGridOperator,
    DetachMaterialsFromDroneTemplateOperator,
    FixConstraintOrderingOperator,
    RecalculateTransitionsOperator,
    ApplyColorsToSelectedDronesOperator,
    SwapColorsInLEDControlPanelOperator,
    TriggerPyroOnSelectedDronesOperator,
    ValidateTrajectoriesOperator,
    SetServerURLOperator,
    SkybrushExportOperator,
    SkybrushCSVExportOperator,
    SkybrushPDFExportOperator,
    SkybrushSKYCAndPDFExportOperator,
    DACExportOperator,
    DDSFExportOperator,
    DrotekExportOperator,
    DSSPathExportOperator,
    DSSPath3ExportOperator,
    EVSKYExportOperator,
    LitebeeExportOperator,
    VVIZExportOperator,
    UseSelectedVertexGroupForFormationOperator,
    GetFormationStatisticsOperator,
    TakeoffOperator,
    LandOperator,
    ReturnToHomeOperator,
    AddMarkersFromStaticCSVOperator,
    AddMarkersFromSVGOperator,
    AddMarkersFromZippedCSVOperator,
    AddMarkersFromZippedDSSOperator,
    AddMarkersFromQRCodeOperator,
    RefreshFileFormatsOperator,
    RunFullProximityCheckOperator,
    UseSharedMaterialForAllDronesMigrationOperator,
)

#: List widgets in this addon.
lists = (SKYBRUSH_UL_lightfxlist, SKYBRUSH_UL_scheduleoverridelist)

#: Menus in this addon
menus = (GenerateMarkersMenu,)

#: Panels in this addon. The order also implicitly defines the order in which
#: our tabs appear in the sidebar of the 3D view.
panels = (
    ShowPanel,
    SwarmPanel,
    FormationsPanel,
    StoryboardEditor,
    TransitionEditorFromCurrentFormation,
    TransitionEditorIntoCurrentFormation,
    LEDControlPanel,
    LightEffectsPanel,
    PyroControlPanel,
    SafetyCheckPanel,
    ExportPanel,
    DroneShowAddonObjectPropertiesPanel,
)

#: Headers in this addon
headers = ()

#: Background tasks in this addon
tasks = (
    InitializationTask(),
    InvalidatePixelCacheTask(),
    PyroEffectsTask(),
    SafetyCheckTask(),
    UpdateLightEffectsTask(),
)

#: Getters for the overlays in this addon, used to disable them before unloading
overlay_getters = (
    partial(get_safety_check_overlay, create=False),
    get_formation_order_overlay,
)


def register():
    register_translations(translations_dict)
    register_state()
    for custom_type in types:
        register_type(custom_type)
    for operator in operators:
        register_operator(operator)
    for list_ in lists:
        register_list(list_)
    for menu in menus:
        register_menu(menu)
    for panel in panels:
        register_panel(panel)
    for header in headers:
        register_header(header)
    for task in tasks:
        task.register()

    Scene.skybrush = PointerProperty(type=DroneShowAddonProperties)
    Object.skybrush = PointerProperty(type=DroneShowAddonObjectProperties)


def unregister():
    for getter in overlay_getters:
        overlay = getter()
        if overlay:
            overlay.enabled = False
    for task in tasks:
        task.unregister()
    for header in reversed(headers):
        unregister_header(header)
    for panel in reversed(panels):
        unregister_panel(panel)
    for menu in menus:
        unregister_menu(menu)
    for list_ in lists:
        unregister_list(list_)
    for operator in reversed(operators):
        unregister_operator(operator)
    for custom_type in reversed(types):
        unregister_type(custom_type)
    unregister_state()
    unregister_translations()
