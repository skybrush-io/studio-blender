import json
from os import environ
import re

from contextlib import contextmanager
from gzip import compress
from http.client import HTTPResponse
from io import IOBase, TextIOWrapper
from natsort import natsorted
from pathlib import Path
from shutil import copyfileobj
from ssl import create_default_context, CERT_NONE
from typing import Any, ContextManager, Dict, List, Optional, Sequence
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from sbstudio.model.light_program import LightProgram
from sbstudio.model.safety_check import SafetyCheckParams
from sbstudio.model.trajectory import Trajectory
from sbstudio.model.types import Coordinate3D
from sbstudio.utils import create_path_and_open

from .errors import SkybrushStudioAPIError

__all__ = ("SkybrushStudioAPI",)


class Response:
    """Class representing a response from the Skybrush Studio API."""

    def __init__(self, response: HTTPResponse):
        """Constructor.

        Parameters:
            response: the raw HTTP response that this object wraps
        """
        self._response = response

    @property
    def content_type(self) -> str:
        """Returns the HTTP content type of the response."""
        info = self._response.info()
        return info.get_content_type()

    def _run_sanity_checks(self) -> None:
        """Runs basic sanity checks on the wrapped HTTP response and raises
        appropriate exceptions when the HTTP response signals an error.
        """
        status_code = self._response.getcode()
        if status_code != 200:
            raise SkybrushStudioAPIError(
                f"Request returned HTTP error code {status_code}"
            )

        if self.content_type not in ("application/octet-stream", "application/json"):
            raise SkybrushStudioAPIError(
                f"Unexpected content type {self.content_type!r} in response"
            )

    def as_bytes(self) -> bytes:
        """Reads the whole response body and returns it as a bytes object."""
        if self.content_type != "application/octet-stream":
            raise SkybrushStudioAPIError("Response type is not an octet stream")
        return self._response.read()

    def as_file_object(self) -> IOBase:
        """Returns the response body as a file-like object."""
        return self._response

    def as_json(self):
        """Parses the response body as JSON and returns the parsed object."""
        if self.content_type != "application/json":
            raise SkybrushStudioAPIError("Response type is not JSON")
        return json.load(TextIOWrapper(self._response, encoding="utf-8"))

    def as_str(self) -> str:
        """Reads the whole response body and return it as a string."""
        if self.content_type not in ["application/octet-stream", "application/json"]:
            raise SkybrushStudioAPIError("Invalid response type")
        data = self._response.read()
        if self.content_type == "application/octet-stream":
            data = data.decode("utf-8")

        return data

    def save_to_file(self, filename: Path) -> None:
        """Writes response to a given file."""
        if self.content_type == "application/octet-stream":
            mode = "wb"
        elif self.content_type == "application/json":
            mode = "w"
        else:
            raise SkybrushStudioAPIError("Invalid response type")
        with create_path_and_open(filename, mode) as f:
            copyfileobj(self._response, f)


_API_KEY_REGEXP = re.compile(r"^[a-zA-Z0-9-_.]*$")


class SkybrushStudioAPI:
    """Class that represents a connection to the API of a Skybrush Studio
    server.
    """

    @staticmethod
    def validate_api_key(key: str) -> str:
        """Validates the given API key.

        Returns:
            the validated API key; same as the input argument

        Raises:
            ValueError: if the key cannot be a valid API key
        """
        if not _API_KEY_REGEXP.match(key):
            raise ValueError("Invalid API key")
        return key

    def __init__(
        self,
        url: str = "https://studio.skybrush.io/api/v1/",
        api_key: Optional[str] = None,
    ):
        """Constructor.

        Parameters:
            url: the root URL of the Skybrush Studio API; defaults to the public
                online service
            api_key: the API key used to authenticate with the server
        """
        self._api_key = None
        self._root = None
        self._request_context = create_default_context()

        self.api_key = api_key
        self.url = url

    @property
    def api_key(self) -> Optional[str]:
        """The API key used to authenticate with the server."""
        return self._api_key

    @api_key.setter
    def api_key(self, value: Optional[str]) -> None:
        self._api_key = self.validate_api_key(value) if value else None

    @property
    def url(self) -> str:
        """The URL where the API can be accessed."""
        return self._root

    @url.setter
    def url(self, value: str) -> None:
        if not value.endswith("/"):
            value += "/"
        self._root = value

    @contextmanager
    def _send_request(self, url: str, data: Any = None) -> ContextManager[Response]:
        """Sends a request to the given URL, relative to the API root, and
        returns the corresponding HTTP response object.

        Parameters:
            url: the URL (relative to the API root) where the request should be
                sent to. The request will be a GET request when the data is
                omitted or `None`, otherwise it will be a POST request.
            data: the body of the request; must be an arbitrary Python object
                that can be encoded as JSON, or a `bytes` object. The content type
                of the request will be determined based on the type of this
                parameter; when `data` is a `bytes` object, it is sent as the
                request body directly and the content type will be
                `application/octet-stream`. When `data` is any other Python
                object, it will be encoded as JSON, compressed with `gzip` and
                then sent as a request with `Content-Type` equal to
                `application/json`.

        Raises:
            SkybrushStudioAPIError: when the request returned a non-successful
                HTTP error code or an invalid content type
        """
        content_encoding = None

        if data is None:
            method = "GET"
        else:
            method = "POST"
            if not isinstance(data, bytes):
                data = json.dumps(data).encode("utf-8")
                content_type = "application/json"
                content_encoding = "gzip"
            else:
                content_type = "application/octet-stream"

        if content_encoding == "gzip":
            data = compress(data)

        headers = {"Content-Type": content_type}
        if content_encoding is not None:
            headers["Content-Encoding"] = content_encoding
        if self._api_key is not None:
            headers["X-Skybrush-API-Key"] = self._api_key

        url = urljoin(self._root, url.lstrip("/"))
        req = Request(url, data=data, headers=headers, method=method)
        with urlopen(req, context=self._request_context) as raw_response:
            response = Response(raw_response)
            response._run_sanity_checks()
            yield response

    def _skip_ssl_checks(self) -> None:
        """Configures the API object to skip SSL checks when making requests.
        This is a _very_ bad practice, but apparently there is some problem with
        the macOS version of Blender that prevents it from finding the system
        certificates, and there are reports that the same problem also applies
        to Linux, hence we provide this method for sake of convenience.
        """
        ctx = create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = CERT_NONE
        self._request_context = ctx

    def export_to_skyc(
        self,
        validation: SafetyCheckParams,
        trajectories: Dict[str, Trajectory],
        lights: Optional[Dict[str, LightProgram]] = None,
        output: Optional[Path] = None,
        show_title: Optional[str] = None,
        show_type: str = "outdoor",
        ndigits: float = 3,
        timestamp_offset: Optional[float] = None,
    ) -> Optional[bytes]:
        """Export drone show data into Skybrush Compiled Format (.skyc).

        Parameters:
            validation: safety check parameters
            trajectories: dictionary of trajectories indexed by drone names
            lights: dictionary of light programs indexed by drone names
            output: the file path where the output should be saved or `None`
                if the output must be returned instead of saving it to a file
            show_title: arbitrary show title; `None` if no title is needed
            show_type: type of the show; must be one of `outdoor` or `indoor`
            ndigits: round floats to this precision
            timestamp_offset: when specified, adds this timestamp offset to the
                metadata of the .skyc file, which is then used later for display
                purposes in Skybrush Viewer

        Note: drone names must match in trajectories and lights

        Returns:
            the drone show data in .skyc format or `None` if an output filename
            was specified
        """

        meta = {}
        if show_title is not None:
            meta["title"] = show_title

        if timestamp_offset is not None:
            meta["timestampOffset"] = timestamp_offset

        if lights is None:
            lights = {name: LightProgram() for name in trajectories.keys()}

        environment = {"type": show_type}

        # TODO(ntamas): add cameras to environment in the "environment" key

        data = {
            "input": {
                "format": "json",
                "data": {
                    "version": 1,
                    "environment": environment,
                    "settings": {"validation": validation.as_dict(ndigits=ndigits)},
                    "swarm": {
                        "drones": [
                            {
                                "type": "generic",
                                "settings": {
                                    "name": name,
                                    "lights": lights[name].as_dict(ndigits=ndigits),
                                    "trajectory": trajectories[name].as_dict(
                                        ndigits=ndigits
                                    ),
                                },
                            }
                            for name in natsorted(trajectories.keys())
                        ]
                    },
                    "meta": meta,
                },
            },
            "output": {"format": "skyc"},
        }

        with self._send_request("operations/render", data) as response:
            if output:
                response.save_to_file(output)
            else:
                return response.as_bytes()

    def generate_plots(
        self,
        trajectories: Dict[str, Trajectory],
        output: Path,
        validation: SafetyCheckParams,
        ndigits: float = 3,
    ) -> None:
        """Export drone show data into Skybrush Compiled Format (.skyc).

        Parameters:
            show_title: arbitrary show title
            trajectories: dictionary of trajectories indexed by drone names
            output: the file path where the output should be saved
            min_distance: desired minimum distance between drones
            max_altitude: maximum allowed altitude for each drone
            max_velocity_xy: maximum allowed horizontal velocity
            max_velocity_z: maximum allowed vertical velocity
            ndigits: round floats to this precision
        """
        data = {
            "input": {
                "format": "json",
                "data": {
                    "version": 1,
                    "settings": {"validation": validation.as_dict(ndigits=ndigits)},
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
                    "plots": "nn,pos,vel",
                    "fps": 5,
                    "single_file": True,
                },
            },
        }

        with self._send_request("operations/render", data) as response:
            response.save_to_file(output)

    def match_points(
        self, source: Sequence[Coordinate3D], target: Sequence[Coordinate3D]
    ) -> List[Optional[int]]:
        """Matches the points of a source point set to the points of a
        target point set in a way that ensures collision-free straight-line
        trajectories between the matched points when neither the source nor the
        target points are too close to each other.
        """
        data = {"version": 1, "source": source, "target": target}
        with self._send_request("operations/match-points", data) as response:
            result = response.as_json()

        if result.get("version") != 1:
            raise SkybrushStudioAPIError("invalid response version")

        return result.get("mapping")

    def plan_transition(
        self,
        source: Sequence[Coordinate3D],
        target: Sequence[Coordinate3D],
        *,
        max_velocity_xy: float,
        max_velocity_z: float,
        max_acceleration: float,
        matching_method: str = "optimal",
    ) -> float:
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
            max_acceleration: maximum allowed acceleration
            matching_method: the algorithm to use when matching source points
                to target points; see the server documentation fof more details.
        """
        if not source or not target:
            return 0.0

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
        with self._send_request("operations/plan-transition", data) as response:
            result = response.as_json()

        if result.get("version") != 1:
            raise SkybrushStudioAPIError("invalid response version")

        start_times = result.get("start_times")
        durations = result.get("durations")
        if start_times is not None and durations is not None:
            return max(
                start_time + duration
                for start_time, duration in zip(start_times, durations)
            )
        else:
            raise SkybrushStudioAPIError("invalid response format")
