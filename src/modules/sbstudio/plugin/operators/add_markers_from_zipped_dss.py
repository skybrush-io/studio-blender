import logging

from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from bpy.path import ensure_ext
from bpy.props import BoolProperty, StringProperty
from bpy_extras.io_utils import ImportHelper

from sbstudio.api import SkybrushStudioAPI

from .base import DynamicMarkerCreationOperator, TrajectoryAndLightProgram
from .add_markers_from_zipped_csv import parse_compressed_csv_zip

__all__ = ("AddMarkersFromZippedDSSOperator",)

log = logging.getLogger(__name__)

#############################################################################
# Helper functions for the importer
#############################################################################


class AddMarkersFromZippedDSSOperator(DynamicMarkerCreationOperator, ImportHelper):
    """Adds markers from .zip compressed DSS .PATH or .PATH3 files
    (each containing baked animation of a single drone) to the currently
    selected formation.
    """

    bl_idname = "skybrush.add_markers_from_zipped_dss"
    bl_label = "Import DSS PATH/PATH3"
    bl_options = {"REGISTER", "UNDO"}

    update_duration = BoolProperty(
        name="Update duration of formation",
        default=True,
        description="Update the duration of the storyboard entry based on animation length",
    )

    # List of file extensions that correspond to DSS files
    filter_glob = StringProperty(default="*.zip", options={"HIDDEN"})
    filename_ext = ".zip"

    def _create_trajectories(self, context) -> dict[str, TrajectoryAndLightProgram]:
        from sbstudio.plugin.api import call_api_from_blender_operator

        filepath = ensure_ext(self.filepath, self.filename_ext)
        with call_api_from_blender_operator(self, "import DSS") as api:
            return parse_compressed_dss_zip(filepath, context, api)

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


def parse_compressed_dss_zip(
    filename: str, context, api: SkybrushStudioAPI
) -> dict[str, TrajectoryAndLightProgram]:
    """Parse a .zip file containing DSS PATH/PATH3 files (one file per drone,
    each containing baked animation with timestamped positions and colors),
    using the Skybrush API.

    Args:
        filename: the name of the .zip input file
        context: the Blender context
        api: the Skybrush Studio API object to call for show file format conversion

    Returns:
        dictionary mapping the imported object names to the corresponding
        timestamps, positions and colors

    Raises:
        RuntimeError: on parse errors
    """

    result: dict[str, TrajectoryAndLightProgram] = {}

    with ZipFile(filename, "r") as zip_file:
        extensions = list(set(Path(x).suffix.lower() for x in zip_file.namelist()))

    if extensions == [".path"]:
        importer = "dss"
    elif extensions == [".path3"]:
        importer = "dss3"
    else:
        raise RuntimeError(f"File extension mismatch in {filename}: {extensions}")

    log.info("Converting DSS show to zipped CSV...")
    show_data = api.convert_show_to_csv(
        filename=filename, importer=importer, fps=context.scene.render.fps
    )

    log.info("Parsing CSV files...")
    result = parse_compressed_csv_zip(BytesIO(show_data))

    return result
