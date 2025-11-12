from contextlib import contextmanager
from typing import Any, Iterator

from sbstudio.plugin.errors import TaskCancelled
from sbstudio.plugin.utils.progress import ProgressHandler, ProgressReport

from .base import SkybrushStudioBaseAPI
from .errors import SkybrushStudioAPIError


__all__ = ("SkybrushGatewayAPI",)


class SkybrushGatewayAPI(SkybrushStudioBaseAPI):
    """Class that represents a connection to the API of a
    Skybrush Gateway for request signing and progress display.
    """

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

    @contextmanager
    def use_new_operation(self, title: str = "") -> Iterator[ProgressHandler]:
        """Returns a progress handler that uses a new operation in Skybrush Gateway.

        Args:
            title: the title of the operation

        Returns:
            a progress handler function
        """
        task_url = self._create_task(title=title)
        last_percentage: float | None = None

        def handler(progress: ProgressReport) -> bool:
            nonlocal last_percentage
            last_percentage = progress.percentage
            with self._send_request(
                task_url,
                {
                    "progress": round(progress.percentage, 1)
                    if progress.percentage is not None
                    else -1,
                    "title": progress.operation,
                },
                compressed=False,
            ) as response:
                cancelled = bool(response.as_json())
                return cancelled

        try:
            yield handler
        except Exception as ex:
            with self._send_request(
                task_url,
                {
                    "completed": True,
                    "error": str(ex) or "An unexpected error occurred",
                    "progress": last_percentage if last_percentage is not None else 0,
                },
                compressed=False,
            ):
                pass  # Response can be ignored
            raise
        except (TaskCancelled, KeyboardInterrupt):
            with self._send_request(
                task_url,
                {
                    "completed": False,
                    "error": "Cancelled by user",
                    "progress": last_percentage if last_percentage is not None else 0,
                },
                compressed=False,
            ):
                pass  # Response can be ignored
            raise
        else:
            with self._send_request(
                task_url,
                {
                    "completed": True,
                    "progress": 100,
                },
                compressed=False,
            ):
                pass  # Response can be ignored
        finally:
            with self._send_request(task_url, method="DELETE"):
                pass  # Response can be ignored

    def _create_task(self, title: str) -> str:
        """Creates a new task in Skybrush Gateway with the given title.

        Args:
            title: the title of the task

        Returns:
            the full normalized URL where updates to the progress of the task can be sent

        Raises:
            SkybrushStudioAPIError: if the task could not be created
        """
        data = {"title": title}
        with self._send_request("task", data, compressed=False) as response:
            if response.status_code != 201:
                raise SkybrushStudioAPIError(
                    f"Progress reporter for {title!r} could not be created"
                )

            task_url = response.get_header("Location")

        if task_url is None:
            raise SkybrushStudioAPIError(
                "Gateway did not return URL for newly created task"
            )

        return self.joined_url(task_url)
