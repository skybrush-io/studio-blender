import logging
import re

from base64 import b64encode
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from natsort import natsorted
from pathlib import Path
from typing import Any, Optional

from sbstudio.model.cameras import Camera
from sbstudio.model.color import Color3D
from sbstudio.model.point import Point3D
from sbstudio.model.light_program import LightProgram
from sbstudio.model.location import ShowLocation
from sbstudio.model.pyro_markers import PyroMarkers
from sbstudio.model.safety_check import SafetyCheckParams
from sbstudio.model.time_markers import TimeMarkers
from sbstudio.model.trajectory import Trajectory
from sbstudio.model.types import Coordinate3D
from sbstudio.model.yaw import YawSetpointList
from sbstudio.plugin.signer import get_signer

from .base import SkybrushStudioResponse, SkybrushStudioBaseAPI
from .constants import COMMUNITY_SERVER_URL
from .errors import SkybrushStudioAPIError
from .types import Limits, Mapping, SmartRTHPlan, TransitionPlan, Version

__all__ = ("SkybrushStudioAPI",)


#############################################################################
# configure logger

log = logging.getLogger(__name__)


_API_KEY_REGEXP = re.compile(r"^[a-zA-Z0-9-_.]*$")
_LICENSE_API_KEY_REGEXP = re.compile(
    r"^License [A-Za-z0-9+/=]{4,}([A-Za-z0-9+/=]{2})*$"
)


class SkybrushStudioAPI(SkybrushStudioBaseAPI):
    """Class that represents a connection to the API of a Skybrush Studio
    server.
    """

    _api_key: Optional[str] = None
    """The API key that will be submitted with each request. For license-type
    API keys, the key must start with the string "License ".
    """

    @contextmanager
    def _sign_and_send_request(
        self, url: str, data: Any = None
    ) -> Iterator[SkybrushStudioResponse]:
        """Sign and send a request."""
        try:
            signer = get_signer()
        except Exception as ex:
            log.warning(f"Could not find request signer: {ex}")
            signer = None
        if signer is not None:
            try:
                signature = signer.sign_request(data)
            except Exception as ex:
                log.warning(f"Could not sign request: {ex}")
                signature = None
        else:
            signature = None
        with self._send_request(url, data, signature=signature) as response:
            yield response

    @staticmethod
    def validate_api_key(key: str) -> str:
        """Validates the given API key.

        Returns:
            the validated API key; same as the input argument

        Raises:
            ValueError: if the key cannot be a valid API key
        """
        if key.startswith("License"):
            if not _LICENSE_API_KEY_REGEXP.match(key):
                raise ValueError("Invalid license-type API key")
        else:
            if not _API_KEY_REGEXP.match(key):
                raise ValueError("Invalid API key")
        return key

    def __init__(
        self,
        url: str = COMMUNITY_SERVER_URL,
        api_key: Optional[str] = None,
        license_file: Optional[str] = None,
    ):
        """Constructor.

        Parameters:
            url: the root URL of the Skybrush Studio API; defaults to the public
                online service
            api_key: the API key used to authenticate with the server
            license_file: the path to a license file to be used as the API Key
        """
        super().__init__(url=url)

        if api_key and license_file:
            raise SkybrushStudioAPIError(
                "Cannot use API key and license file at the same time"
            )

        if license_file:
            self.api_key = self._convert_license_file_to_api_key(license_file)
        else:
            self.api_key = api_key

    @property
    def api_key(self) -> Optional[str]:
        """The API key used to authenticate with the server."""
        return self._api_key

    @api_key.setter
    def api_key(self, value: Optional[str]) -> None:
        self._api_key = self.validate_api_key(value) if value else None

    def _convert_license_file_to_api_key(self, file: str) -> str:
        """Parses a license file and transforms it to an API key.

        Returns:
            the license file parsed as an API key

        Raises:
            ValueError: if the file cannot be read as an API key
        """
        if not Path(file).exists():
            raise ValueError("License file does not exist")

        try:
            with open(file, "rb") as fp:
                api_key = f"License {b64encode(fp.read()).decode('ascii')}"
        except Exception:
            raise ValueError("Could not read license file") from None

        return api_key

    def decompose_points(
        self,
        points: Sequence[Coordinate3D],
        *,
        min_distance: float,
        method: str = "greedy",
    ) -> list[int]:
        """Decomposes a set of points into multiple groups while ensuring that
        the minimum distance of points within the same group is at least as
        large as the given threshold.
        """
        data = {
            "version": 1,
            "method": str(method),
            "min_distance": float(min_distance),
            "points": points,
        }
        with self._sign_and_send_request("operations/decompose", data) as response:
            result = response.as_json()

        if result.get("version") != 1:
            raise SkybrushStudioAPIError("invalid response version")

        return result.get("groups")

    def export(
        self,
        *,
        validation: SafetyCheckParams,
        trajectories: dict[str, Trajectory],
        lights: Optional[dict[str, LightProgram]] = None,
        pyro_programs: Optional[dict[str, PyroMarkers]] = None,
        yaw_setpoints: Optional[dict[str, YawSetpointList]] = None,
        output: Optional[Path] = None,
        show_title: Optional[str] = None,
        show_type: str = "outdoor",
        show_location: ShowLocation | None = None,
        show_segments: Optional[dict[str, tuple[float, float]]] = None,
        ndigits: int = 3,
        timestamp_offset: Optional[float] = None,
        time_markers: Optional[TimeMarkers] = None,
        cameras: Optional[list[Camera]] = None,
        renderer: str | list[str] = "skyc",
        renderer_params: Optional[
            dict[str, Any] | list[Optional[dict[str, Any]]]
        ] = None,
    ) -> Optional[bytes]:
        """
        Export drone show data.

        Parameters:
            validation: Safety check parameters.
            trajectories: Dictionary of trajectories indexed by drone names.
            lights: Dictionary of light programs indexed by drone names.
            pyro_programs: Dictionary of pyro programs indexed by drone names.
            yaw_setpoints: Dictionary of yaw setpoints indexed by drone names.
            output: The file path where the output should be saved or `None`
                if the output must be returned instead of saving it to a file.
            show_title: Arbitrary show title; `None` if no title is needed.
            show_type: Type of the show; must be one of `outdoor` or `indoor`.
            show_location: When specified, defines the show origin and
                orientation in the real world.
            show_segments: Dictionary that maps show segment IDs to a start
                (inclusive) and end (exclusive) timestamp pair.
            ndigits: Round floats to this precision.
            timestamp_offset: When specified, adds this timestamp offset to the
                show metadata, which can later be used for display purposes in
                Skybrush Viewer.
            time_markers: When specified, time markers will be exported as
                temporal cues.
            cameras: When specified, list of cameras to include in the environment.
            renderer: The renderer(s) to use to export the show.
            renderer_params: Extra parameters for the renderer(s).

        Note: drone names must match in trajectories and lights

        Returns:
            The exported drone show data or `None` if an `output` filename
            was specified.
        """

        meta = {}
        if show_title is not None:
            meta["title"] = show_title

        if timestamp_offset is not None:
            meta["timestampOffset"] = timestamp_offset

        if show_segments is not None:
            meta["segments"] = show_segments

        if lights is None:
            lights = {name: LightProgram() for name in trajectories.keys()}

        environment: dict[str, Any] = {"type": show_type}

        if cameras:
            environment["cameras"] = [
                camera.as_dict(ndigits=ndigits) for camera in cameras
            ]

        if show_location:
            environment["location"] = show_location.json

        if time_markers is None:
            time_markers = TimeMarkers()

        # TODO: add music to the "media" key

        def format_drone(name: str):
            settings = {
                "name": name,
                "lights": lights[name].as_dict(ndigits=ndigits),
                "trajectory": trajectories[name].as_dict(ndigits=ndigits),
            }

            if pyro_programs is not None:
                import bpy

                fps = bpy.context.scene.render.fps

                settings["pyro"] = pyro_programs[name].as_api_dict(
                    fps=fps, ndigits=ndigits
                )
            if yaw_setpoints is not None:
                settings["yawControl"] = yaw_setpoints[name].as_dict(ndigits=ndigits)

            return {"type": "generic", "settings": settings}

        data: dict[str, Any] = {
            "input": {
                "format": "json",
                "data": {
                    "version": 1,
                    "environment": environment,
                    "settings": {
                        "cues": time_markers.as_dict(ndigits=ndigits),
                        "validation": validation.as_dict(ndigits=ndigits),
                    },
                    "swarm": {
                        "drones": [
                            format_drone(name)
                            for name in natsorted(trajectories.keys())
                        ]
                    },
                    "meta": meta,
                },
            },
        }

        if isinstance(renderer, (list, tuple)):
            operation = "multi-render"
            if renderer_params is None:
                renderer_params = [None] * len(renderer)  # type: ignore
            assert isinstance(renderer_params, (list, tuple))
            data["outputs"] = [
                {"format": format, "parameters": parameters or {}}
                for format, parameters in zip(renderer, renderer_params, strict=True)
            ]
        else:
            operation = "render"
            data["output"] = {}
            data["output"]["format"] = renderer
            if renderer_params is not None:
                data["output"]["parameters"] = renderer_params

        with self._sign_and_send_request(f"operations/{operation}", data) as response:
            if output:
                response.save_to_file(output)
            else:
                return response.as_bytes()

    def convert_show_to_csv(
        self,
        filename: str,
        importer: str,
        *,
        fps: int = 5,
    ) -> bytes:
        """
        Convert an entire drone show or a single formation from an external file
        into Skybrush-compatible csv format.

        Parameters:
            filename: the filename to import and convert
            importer: the importer to use to import the show/formation
            fps: the FPS value to use in the csv output

        Returns:
            The imported drone show data as a bytes object containing
                zipped .csv files
        """

        with open(filename, "rb") as zip_file:
            input_data = b64encode(zip_file.read()).decode("ascii")

        data = {
            "input": {
                "format": importer,
                "data": input_data,
                "parameters": {"simplify": False},
            },
            "output": {
                "format": "csv",
                "parameters": {"fps": fps},
            },
        }

        with self._sign_and_send_request("operations/render", data) as response:
            result = response.as_bytes()

        return result

    def create_formation_from_svg(
        self,
        source: str,
        num_points: int,
        size: float,
        angle: float,
    ) -> tuple[list[Point3D], list[Color3D]]:
        """Samples the path objects of an SVG string into a list of coordinates
        and corresponding colors.

        Args:
            source: the SVG source string
            n: the number of points to generate
            size: the maximum extent of the returned points along the main axes
            angle: the mimimum angle change at path nodes to treat them as corners

        Returns:
            the list of evenly sampled points and corresponding colors

        """
        data = {
            "version": 1,
            "method": "svg",
            "parameters": {
                "version": 1,
                "source": source,
                "n": num_points,
                "size": size,
                "angle": angle,
            },
        }

        with self._sign_and_send_request(
            "operations/create-static-formation", data
        ) as response:
            result = response.as_json()

        if result.get("version") != 1:
            raise SkybrushStudioAPIError("invalid response version")

        points = [Point3D(*point) for point in result.get("points")]
        colors = [Color3D(*color) for color in result.get("colors")]

        return points, colors

    def generate_plots(
        self,
        trajectories: dict[str, Trajectory],
        output: Path,
        validation: SafetyCheckParams,
        plots: Sequence[str] = ("stats", "pos", "vel", "drift", "nn"),
        fps: float = 4,
        ndigits: int = 3,
        time_markers: Optional[TimeMarkers] = None,
    ) -> None:
        """Export drone show data into Skybrush Compiled Format (.skyc).

        Parameters:
            trajectories: dictionary of trajectories indexed by drone names
            output: the file path where the output should be saved
            validation: safety check settings to use during validation
            plots: the type of plots to render
            fps: number of frames per second in the plots [1/s]
            ndigits: round floats to this precision
            time_markers: temporal cues to use in the plots
        """

        if time_markers is None:
            time_markers = TimeMarkers()

        data = {
            "input": {
                "format": "json",
                "data": {
                    "version": 1,
                    "settings": {
                        "cues": time_markers.as_dict(ndigits=ndigits),
                        "validation": validation.as_dict(ndigits=ndigits),
                    },
                    "swarm": {
                        "drones": [
                            {
                                "type": "generic",
                                "settings": {
                                    "name": name,
                                    "trajectory": trajectories[name].as_dict(
                                        ndigits=ndigits
                                    ),
                                },
                            }
                            for name in natsorted(trajectories.keys())
                        ]
                    },
                    "meta": {},
                },
            },
            "output": {
                "format": "plot",
                "parameters": {
                    "plots": ",".join(plots),
                    "fps": fps,
                    "single_file": True,
                },
            },
        }

        with self._sign_and_send_request("operations/render", data) as response:
            response.save_to_file(output)

    def get_limits(self) -> Limits:
        """Returns the limits and supported file formats of the server."""
        with self._sign_and_send_request("queries/limits") as response:
            return Limits.from_json(response.as_json())

    def get_version(self) -> Version:
        """Returns the version of the server."""
        with self._sign_and_send_request("queries/version") as response:
            return Version.from_json(response.as_json())

    def match_points(
        self,
        source: Sequence[Coordinate3D],
        target: Sequence[Coordinate3D],
        *,
        radius: Optional[float] = None,
    ) -> tuple[Mapping, Optional[float]]:
        """Matches the points of a source point set to the points of a
        target point set in a way that ensures collision-free straight-line
        trajectories between the matched points when neither the source nor the
        target points are too close to each other.

        Returns:
            the mapping and the minimum clearance between points during the
            transition; ``None`` if not known or not calculated due to
            efficiency reasons
        """
        data = {"version": 1, "source": source, "target": target}
        if radius is not None:
            data["radius"] = radius

        with self._sign_and_send_request("operations/match-points", data) as response:
            result = response.as_json()

        if result.get("version") != 1:
            raise SkybrushStudioAPIError("invalid response version")

        return result.get("mapping"), result.get("clearance")

    def plan_landing(
        self,
        points: Sequence[Coordinate3D],
        *,
        min_distance: float,
        velocity: float,
        target_altitude: float = 0,
        spindown_time: float = 5,
    ) -> tuple[list[int], list[int]]:
        """Plans the landing trajectories for a set of drones, assuming that
        they should maintain a given minimum distance while the motors are
        running and that they land with constant speed.

        Arguments:
            points: coordinates of the drones to land
            min_distance: minimum distance to maintain while the motors are
                running
            velocity: average vertical velocity during landing
            target_altitude: altitude to land the drones to
            spindown_time: number of seconds it takes for the motors to
                shut down after a successful landing

        Returns:
            the start times and durations of the landing operation for each drone
        """
        data = {
            "version": 1,
            "points": points,
            "min_distance": float(min_distance),
            "velocity": float(velocity),
            "target_altitude": float(target_altitude),
            "spindown_time": float(spindown_time),
        }
        with self._sign_and_send_request("operations/plan-landing", data) as response:
            result = response.as_json()

        if result.get("version") != 1:
            raise SkybrushStudioAPIError("invalid response version")

        return result["start_times"], result["durations"]

    def plan_smart_rth(
        self,
        source: Sequence[Coordinate3D],
        target: Sequence[Coordinate3D],
        *,
        max_velocity_xy: float,
        max_velocity_z: float,
        max_acceleration: float,
        min_distance: float,
        rth_model: str = "straight_line_with_neck",
    ) -> SmartRTHPlan:
        """Proposes starting times for predefined smart RTH procedures
        between source and target with the given parameters.

        Parameters:
            source: the list of source points
            target: the list of target points
            max_velocity_xy: maximum allowed velocity in the XY plane
            max_velocity_z: maximum allowed velocity along the Z axis
            max_acceleration: maximum allowed acceleration
            min_distance: minimum distance to maintain during the transition
            rth_model: the smart RTH model to use when matching source points
                to target points; see the server documentation for more details.
        """
        if not source or not target:
            return SmartRTHPlan.empty()

        data = {
            "version": 1,
            "source": source,
            "target": target,
            "max_velocity_xy": max_velocity_xy,
            "max_velocity_z": max_velocity_z,
            "max_acceleration": max_acceleration,
            "min_distance": min_distance,
            "rth_model": rth_model,
        }

        with self._sign_and_send_request("operations/plan-smart-rth", data) as response:
            result = response.as_json()

        if result.get("version") != 1:
            raise SkybrushStudioAPIError("invalid response version")

        start_times = result.get("start_times")
        if start_times is None:
            raise SkybrushStudioAPIError(
                "invalid response format, start times are missing"
            )
        durations = result.get("durations")
        if durations is None:
            raise SkybrushStudioAPIError(
                "invalid response format, durations are missing"
            )
        inner_points = result.get("inner_points")
        if inner_points is None:
            raise SkybrushStudioAPIError(
                "invalid response format, inner points are missing"
            )

        return SmartRTHPlan(
            start_times=list(start_times),
            durations=list(durations),
            inner_points=list(inner_points),
        )

    def plan_transition(
        self,
        source: Sequence[Coordinate3D],
        target: Sequence[Coordinate3D],
        *,
        max_velocity_xy: float,
        max_velocity_z: float,
        max_acceleration: float,
        max_velocity_z_up: Optional[float] = None,
        matching_method: str = "optimal",
    ) -> TransitionPlan:
        """Proposes a minimum feasible duration for a transition between the
        given source and target points, assuming that the drones move in a
        straight line, they are stationary in the beginning and in the end,
        and they are allowed to move with the given maximum velocities and
        accelerations.

        Parameters:
            source: the list of source points
            target: the list of target points
            max_velocity_xy: maximum allowed velocity in the XY plane
            max_velocity_z: maximum allowed velocity along the Z axis
            max_velocity_z_up: maximum allowed velocity along the Z axis, upwards,
                if it is different from the maximum allowed velocity downwards.
                `None` means that it is the same as the Z velocity constraint
                downwards
            max_acceleration: maximum allowed acceleration
            matching_method: the algorithm to use when matching source points
                to target points; see the server documentation for more details.
        """
        if not source or not target:
            return TransitionPlan.empty()

        data = {
            "version": 1,
            "source": source,
            "target": target,
            "max_velocity_xy": max_velocity_xy,
            "max_velocity_z": max_velocity_z,
            "max_acceleration": max_acceleration,
            "transition_method": "const_jerk",
            "matching_method": matching_method,
        }

        if max_velocity_z_up is not None:
            data["max_velocity_z_up"] = max_velocity_z_up

        with self._sign_and_send_request(
            "operations/plan-transition", data
        ) as response:
            result = response.as_json()

        if result.get("version") != 1:
            raise SkybrushStudioAPIError("invalid response version")

        start_times = result.get("start_times")
        durations = result.get("durations")
        if start_times is None or durations is None:
            raise SkybrushStudioAPIError("invalid response format")

        mapping = result.get("mapping")
        clearance = result.get("clearance")

        return TransitionPlan(
            start_times=list(start_times),
            durations=list(durations),
            mapping=list(mapping) if mapping is not None else None,
            clearance=float(clearance) if clearance is not None else None,
        )
