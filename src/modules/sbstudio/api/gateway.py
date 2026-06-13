from contextlib import contextmanager
from typing import Iterator

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

    def sign_request(self, data: bytes) -> str:
        """Signs a JSON request issued by Skybrush Studio.

        Args:
            data: the raw data to sign

        Returns:
            the signed data to be sent to Skybrush Studio Server
        """
        with self._send_request("sign", data=data, allow_compression=False) as response:
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
                json={
                    "progress": round(progress.percentage, 1)
                    if progress.percentage is not None
                    else -1,
                    "title": progress.operation,
                },
            ) as response:
                cancelled = bool(response.as_json())
                return cancelled

        try:
            yield handler
        except (TaskCancelled, KeyboardInterrupt):
            with self._send_request(
                task_url,
                json={
                    "cancelled": True,
                    "completed": False,
                    "error": "Cancelled by user",
                    "progress": last_percentage if last_percentage is not None else 0,
                },
            ):
                pass  # Response can be ignored
            raise
        except Exception as ex:
            with self._send_request(
                task_url,
                json={
                    "completed": False,
                    "error": str(ex) or "An unexpected error occurred",
                    "progress": last_percentage if last_percentage is not None else 0,
                },
            ):
                pass  # Response can be ignored
            raise
        else:
            with self._send_request(
                task_url,
                json={
                    "completed": True,
                    "progress": 100,
                },
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
        with self._send_request("task", json={"title": title}) as response:
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
