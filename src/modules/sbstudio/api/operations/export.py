from natsort import natsorted
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict

from sbstudio.model.light_program import LightProgram
from sbstudio.model.trajectory import Trajectory

from ..enums import SkybrushJSONFormat

from .base import SkybrushAPIOperationBase

__all__ = ("SkybrushExporter",)


class SkybrushExporter(SkybrushAPIOperationBase):
    """Class for exporting drone show data into Skybrush-compatible formats."""

    def __init__(
        self,
        show_title: str,
        trajectories: Dict[str, Trajectory],
        lights: Dict[str, LightProgram],
    ):
        """Class initialization.

        Parameters:
            show_title: arbitrary show title
            trajectories: dictionary of trajectories indexed by drone names
            lights: dictionary of light programs indexed by drone names


        Note: drone names must match in trajectories and lights

        """
        self._show_title = show_title
        if sorted(trajectories.keys()) != sorted(lights.keys()):
            raise ValueError(
                "Trajectories and lights must contain equal number of items, one for each drone."
            )
        self._trajectories = trajectories
        self._lights = lights

    def _drone_data_as_dict(self, name: str, ndigits: int = 3) -> dict:
        """Create a Skybrush-compatible dictionary representation of all data
        related to a single drone stored in self.

        Parameters:
            name: the name of the given drone in self database
            ndigits: round floats to this precision

        Return:
            dictionary representation of drone data
        """
        return {
            "type": "generic",
            "settings": {
                "name": name,
                "lights": self._lights[name].as_dict(ndigits=ndigits),
                "trajectory": self._trajectories[name].as_dict(ndigits=ndigits),
            },
        }

    def as_dict(self, format: SkybrushJSONFormat, ndigits: int = 3) -> dict:
        """Create a Skybrush-compatible dictionary representation of the whole
        drone show stored in self.

        Parameters:
            format: the format of the output
            ndigits: round floats to this precision

        Return:
            dictionary representation of self
        """

        data = {
            "version": 1,
            "settings": {},
            "swarm": {
                "drones": [
                    self._drone_data_as_dict(name, ndigits=ndigits)
                    for name in natsorted(self._trajectories.keys())
                ]
            },
            "meta": {"title": self._show_title},
        }

        if format == SkybrushJSONFormat.RAW:
            return data
        elif format == SkybrushJSONFormat.ONLINE:
            return {
                "input": {"format": "json", "data": data},
                "output": {"format": "skyc"},
            }
        else:
            raise NotImplementedError("Unknown Skybrush JSON format")

    def to_skyc(self, output: Path) -> None:
        """Write a Skybrush Compiled Format (.skyc) representation of the
        drone show stored in self to the given output file.

        Parameters:
            output: the filename where the output content will be written

        """

        try:
            from skybrush.io.base.importer import find_importer_function, ImportContext
            from skybrush.io.base.renderer import find_renderer_function, RenderContext

            is_skybrush_installed = True
        except ImportError:
            is_skybrush_installed = False

        # temporary hack to see intermediate results
        # self.save_to_json(r"d:\download\temp.json", format=SkybrushJSONFormat.RAW)
        # return

        if is_skybrush_installed:
            with TemporaryDirectory() as work_dir:
                # first create a temporary JSON representation
                json_output = Path(work_dir) / Path("show.json")
                self.save_to_json(json_output, format=SkybrushJSONFormat.RAW)
                # then send it to skybrush to convert it to .skyc
                importer = find_importer_function("skybrush.io.json.importer")
                context = ImportContext()
                parameters = {}
                world = importer([json_output], context, parameters)
                renderer = find_renderer_function("skybrush.io.skyc.renderer")
                context = RenderContext()
                parameters = {"output": output}
                renderer(world, context, parameters)
        else:
            # if Skybrush Studio is not present locally, try to convert online
            self._ask_skybrush_studio_server("render", output)
