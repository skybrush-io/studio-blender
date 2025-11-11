from __future__ import annotations

from abc import abstractmethod, ABC
from itertools import chain
from time import time
from typing import Callable, Iterable, Iterator, Protocol, TypeVar

from sbstudio.plugin.errors import SkybrushStudioTaskCancelledError

__all__ = (
    "ProgressReport",
    "ProgressHandler",
    "StepBasedProgressReport",
    "FrameRange",
    "report_progress",
)


T = TypeVar("T")


class ProgressReport(Protocol):
    """Represents a progress report yielded periodically from a long-running
    operation.

    This interface specification is intentionally kept as minimal as possible.
    If your operation consists of discrete steps, you can use
    StepBasedProgrssReport_ as your base class.
    """

    operation: str | None
    """Optional string that describes the operation being executed."""

    @property
    def finished(self) -> bool:
        """Whether the operation has finished.

        Note that this is not necessarily equivalent to having reached 100%.
        Being finished means that we have committed ourselves that no further
        updates will be posted for this progress report.

        Implementors _may_ choose to implement this method in a way that having
        a progress of 100% implies being finished, but this is not required.
        """
        ...

    @property
    def percentage(self) -> float | None:
        """The percentage of the operation that has been completed, or ``None`` if
        the percentage is unknown.
        """
        ...

    @property
    def remaining_time(self) -> float | None:
        """Calculates remaining time in seconds or None if not known."""
        ...

    def format(self) -> str:
        """Formats the progress report as a human-readable string."""
        ...


class ProgressReportBase(ABC, ProgressReport):
    """Abstract base class for progress reports that implements the common
    logic behind the estimation of remaining time.
    """

    operation: str | None = None
    """Optional string that describes the operation being executed."""

    _started_at: float | None = None
    """Start time of the operation; updated automatically when `start()` is
    called.
    """

    _finished_at: float | None = None
    """Completion time of the operation; updated automatically when `finish()` is
    called.
    """

    _last_updated_at: float | None = None
    """Time when the progress information was updated most recently. Used to
    calculate the time remaining.
    """

    def __init__(self, *, operation: str | None = None):
        self.operation = operation

    @property
    def finished(self) -> bool:
        return self._finished_at is not None

    @property
    @abstractmethod
    def percentage(self) -> float | None: ...

    @property
    def remaining_time(self) -> float | None:
        if self.finished:
            return 0.0
        elif (
            not self.percentage
            or self._last_updated_at is None
            or self._started_at is None
            or self._last_updated_at == self._started_at
        ):
            return None
        else:
            return (
                (self._last_updated_at - self._started_at)
                * (100 - self.percentage)
                / self.percentage
            )

    @abstractmethod
    def format(self) -> str: ...

    def start(self, operation: str | None = None, now: float | None = None) -> None:
        """Marks the start time of the progress report."""
        if now is None:
            now = time()

        if self._started_at is not None:
            raise RuntimeError("Progress report has already been started")

        if operation is not None:
            self.operation = operation

        self._started_at = now
        self._touch(now)

    def finish(self, now: float | None = None) -> None:
        """Marks the progress report as finished."""
        if self._started_at is None:
            raise RuntimeError("Progress report has not been started yet")

        if now is None:
            now = time()

        self._finished_at = now
        self._touch(now)

    def _touch(self, now: float | None = None) -> None:
        """Updates the last updated time to now."""
        self._last_updated_at = time() if now is None else now


class StepBasedProgressReport(ProgressReportBase):
    """Represents a progress report yielded periodically from a long-running
    operation consisting of discrete steps.
    """

    _steps_done: int = 0
    """Number of steps already performed in the operation."""

    _num_steps: int | None
    """Total number of steps in the operation; ``None`` if unknown."""

    def __init__(self, num_steps: int | None = None, *, operation: str | None = None):
        super().__init__(operation=operation)
        self._num_steps = num_steps

    @property
    def percentage(self) -> float | None:
        """Percentage of the operation that has been completed, or ``None`` if
        the percentage is unknown.
        """
        if self._num_steps is None or self._num_steps < 1:
            return None
        else:
            return self._steps_done / self._num_steps * 100

    @property
    def remaining_time_str(self) -> str | None:
        """Shows the remaining time as a mm:ss formatted string
        or None if not known"""
        if self.remaining_time is None:
            return None
        elif self.remaining_time < 0:
            minutes, seconds = divmod(int(-self.remaining_time), 60)
            return f"-{minutes:02d}:{seconds:02d}"
        else:
            minutes, seconds = divmod(int(self.remaining_time), 60)
            return f"{minutes:02d}:{seconds:02d}"

    def add_step(self) -> None:
        """Registers that one step has been performed."""
        self.add_steps(1)

    def add_steps(self, count: int) -> None:
        """Registers that the given number of steps have been performed."

        Args:
            count: number of steps to add
        """
        self._steps_done += count
        self._touch()

    def format(self) -> str:
        time_left = (
            ""
            if self.remaining_time_str is None
            else f", {self.remaining_time_str} mins left"
        )
        if self._num_steps is None:
            return (
                f"{self.operation}: {self._steps_done} step(s) done, "
                f"{self.percentage or 0:.1f}%{time_left}"
            )
        else:
            return (
                f"{self.operation}: {self._steps_done}/{self._num_steps}, "
                f"{self.percentage:.1f}%{time_left}"
            )


ProgressHandler = Callable[[ProgressReport], bool]
"""Type alias for functions that handle progress reports.
Return value of `True` means that the task needs to be cancelled."""


def report_progress(
    iterable: Iterable[T],
    *,
    size_hint: int | None = None,
    operation: str | None = None,
    throttle: float | bool = True,
    report_factory: Callable[[int | None], StepBasedProgressReport],
    on_advance: Callable[[ProgressReport, T], None] | None = None,
    on_progress: ProgressHandler | None = None,
) -> Iterator[T]:
    """Wraps an iterable to report progress on its consumption.

    Args:
        iterable: the iterable to wrap
        operation: optional operation description
        on_progress: optional callback to call with progress reports

    Returns:
        another iterator that calls the on_progress callback when the
        progress is updated.
    """
    if size_hint is not None:
        total_items = size_hint
    else:
        try:
            total_items = len(iterable)  # type: ignore[arg-type]
        except TypeError:
            total_items = None

    progress: StepBasedProgressReport = report_factory(total_items)
    progress.start(operation)

    callback_called_at = 0

    if isinstance(throttle, (int, float)):
        throttle_interval = float(throttle)
    elif throttle:
        throttle_interval = 0.5
    else:
        throttle_interval = 0.0

    try:
        for item in iterable:
            yield item

            now = time()
            progress.add_step()
            if on_advance:
                on_advance(progress, item)
            if on_progress and now - callback_called_at >= throttle_interval:
                cancelled = on_progress(progress)
                callback_called_at = now
                if cancelled:
                    raise SkybrushStudioTaskCancelledError(
                        f"Cancelled operation: {operation}"
                    )

    finally:
        progress.finish()
        if on_progress:
            cancelled = on_progress(progress)
            if cancelled:
                raise SkybrushStudioTaskCancelledError(
                    f"Cancelled operation: {operation}"
                )


class FrameRange:
    """Class that represents a range of frames, both ends inclusive, and an
    associated step size.
    """

    _start: int
    """The start frame. It is guaranteed to be yielded first."""

    _end: int
    """The end frame. It is guaranteed to be yielded last if it is larger than
    or equal to the start frame, even if the step does not divide the range
    evenly.
    """

    _fps: int
    """Number of frames per second."""

    def __init__(
        self,
        start: int,
        end: int,
        fps: int,
    ):
        self._start = start
        self._end = max(start, end)
        self._fps = fps

    def iter(
        self,
        fps: int = 1,
        *,
        operation: str | None = None,
        on_progress: ProgressHandler | None = None,
    ) -> Iterator[int]:
        frame_step = max(1, int(self._fps // fps))

        dist = self._end - self._start
        if dist < 0:
            return iter([])

        if dist == 0:
            it = [self._start]

        if dist % frame_step == 0:
            it = range(self._start, self._end + 1, frame_step)
            size_hint = len(it)
        else:
            it = range(self._start, self._end, frame_step)
            size_hint = len(it) + 1
            it = chain(it, [self._end])

        def _report_factory(num_steps: int | None) -> StepBasedProgressReport:
            return _FrameIteratorProgressReport(
                frame_range=(self._start, self._end),
                step=frame_step,
            )

        def _on_advance(
            progress: ProgressReport,
            frame: int,
        ) -> None:
            if isinstance(progress, _FrameIteratorProgressReport):
                progress.current_frame = frame

        return report_progress(
            it,
            size_hint=size_hint,
            operation=operation,
            report_factory=_report_factory,
            on_advance=_on_advance,
            on_progress=on_progress,
        )


class _FrameIteratorProgressReport(StepBasedProgressReport):
    """Represents a progress report yielded periodically from a long-running
    operation that works on individual Blender frames.
    """

    frame_range: tuple[int, int] = (0, 0)
    """Frame range of the operation."""

    current_frame: int = 0
    """Current frame that the operation is being executed on."""

    def __init__(
        self,
        frame_range: tuple[int, int],
        step: int,
        *,
        operation: str | None = None,
    ):
        start, end = frame_range

        total_steps, remainder = divmod(end - start, step)
        total_steps += 2 if remainder else 1

        self.frame_range = frame_range

        super().__init__(num_steps=total_steps, operation=operation)

    def format(self) -> str:
        time_left = (
            ""
            if self.remaining_time_str is None
            else f", {self.remaining_time_str} mins left"
        )
        return (
            f"{self.operation}: frame {self.current_frame} in range {self.frame_range!r}, "
            f"{self.percentage:.1f}%{time_left}"
        )
