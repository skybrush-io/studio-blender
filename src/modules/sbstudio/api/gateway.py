from typing import Any

from sbstudio.plugin.utils.progress import ProgressReport

from .base import SkybrushStudioBaseAPI
from .errors import SkybrushStudioAPIError


__all__ = ("SkybrushGatewayAPI",)


class SkybrushGatewayAPI(SkybrushStudioBaseAPI):
    """Class that represents a connection to the API of a
    Skybrush Gateway for request signing and progress display.
    """

    _progress_task_url: str | None = None
    """Relative URL of the current progress reporter initialized."""

    def get_hardware_id(self) -> str:
        """Gets the hardware ID of the current machine from the Studio Gateway."""
        with self._send_request("hwid") as response:
            return response.as_str()

    def sign_request(self, data: Any, *, compressed: bool | None = None) -> str:
        """Signs a JSON request issued by Skybrush Studio.

        Args:
            data: the raw or compressed data to sign
            compressed: whether data is an already gzip-compressed JSON-object (True),
                a JSON-object not to be compressed (False), or an object to be compressed
                if applicable (None)

        Returns:
            the signed data to be sent to Skybrush Studio Server
        """
        with self._send_request(
            "sign", data=data, compressed=compressed, method="POST"
        ) as response:
            return response.as_str()

    def show_progress(self, progress: ProgressReport) -> None:
        """Shows the progress of the given progress report in Skybrush Gateway.

        Note that only one progress reporter can be used at a time.
        """
        if self._progress_task_url is None:
            self._init_progress(title=progress.operation or "Progress")

        self._set_progress(progress=progress.percentage or 0)

        if progress.finished:
            self._close_progress()

    def _close_progress(self) -> None:
        """Closes the current progress task reporter."""
        if self._progress_task_url is not None:
            with self._send_request(
                self._progress_task_url, method="DELETE"
            ) as _response:
                pass  # TODO: what to do with the result?
            self._progress_task_url = None

    def _init_progress(self, title: str) -> None:
        """Initializes a progress reporter in Skybrush Gateway with the given title.

        Args:
            title: the title of the progress reporter

        Raises:
            SkybrushStudioAPIError if the progress reporter could not be initialized

        """
        data = {"title": title, "progress": 0}
        with self._send_request("task", data, compressed=False) as response:
            if response.status_code != 201:
                raise SkybrushStudioAPIError(
                    f"Progress reporter for {title!r} could not be initialized"
                )

            task_url = response.get_header("Location")
            if task_url is None:
                raise SkybrushStudioAPIError("Gateway did not return progress task URL")
            task_url = task_url.lstrip("/")

            if self._progress_task_url and task_url != self._progress_task_url:
                self._close_progress()
            self._progress_task_url = task_url

    def _set_progress(self, progress: float) -> None:
        """Sets the progress reporter of the Skybrush Gateway to the given value.

        Args:
            progress: the progress to show
        """
        if self._progress_task_url is not None:
            data = {"progress": progress}
            with self._send_request(
                self._progress_task_url, data, compressed=False
            ) as _response:
                pass  # TODO: what to do with the result?
