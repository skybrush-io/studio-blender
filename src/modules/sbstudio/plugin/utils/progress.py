from dataclasses import dataclass
from time import time
from typing import Callable, Iterator, Optional, Tuple

__all__ = ("ProgressReport", "FrameProgressReport")


@dataclass
class ProgressReport:
    """Represents a progress report yielded periodically from a long-running
    operation.
    """

    steps_done: int = 0
    """Number of steps already performed in the operation."""

    total_steps: Optional[int] = None
    """Total number of steps in the operation; ``None`` if unknown."""

    operation: Optional[str] = None
    """Optional string that describes the operation being executed."""

    start_time: float | None = None
    """Optional user updated start time of the progress procedure."""

    current_time: float | None = None
    """Optional user updated current time of the progress procedure."""

    @property
    def remaining_time(self) -> float | None:
        """Calculates remaining time in seconds or None if not known."""
        if not self.percentage or self.current_time is None or self.start_time is None:
            return None

        return (
            (self.current_time - self.start_time)
            * (100 - self.percentage)
            / self.percentage
        )

    @property
    def remaining_time_str(self) -> str | None:
        """Shows the remaining time as a mm:ss formatted string
        or None if not known"""
        if self.remaining_time is None:
            return None
        return (
            f"{int(self.remaining_time / 60):02d}:{int(self.remaining_time % 60):02d}"
        )

    @property
    def percentage(self) -> Optional[float]:
        """Percentage of the operation that has been completed."""
        if self.total_steps is None or self.total_steps < 1:
            return None
        return self.steps_done / self.total_steps * 100

    def format(self) -> str:
        time_left = (
            ""
            if self.remaining_time_str is None
            else f", {self.remaining_time_str} mins left"
        )
        return (
            f"{self.operation}: {self.steps_done}/{self.total_steps}, "
            f"{self.percentage:.1f}%{time_left}"
        )


@dataclass
class FrameProgressReport(ProgressReport):
    """Represents a progress report yielded periodically from a long-running
    operation that works on individual Blender frames.
    """

    frame_range: Tuple[int, int] = (0, 0)
    """Frame range of the operation."""

    current_frame: int = 0
    """Current frame that the operation is being executed on."""

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


class FrameIterator(Iterator[int]):
    """Iterator that yields frame numbers within a given frame range."""

    start: int
    """The start frame. It is guaranteed to be yielded first."""

    end: int
    """The end frame. It is guaranteed to be yielded last if it is larger than
    or equal to the start frame, even if the step does not divide the range evenly.
    """

    step: int
    """Step between consecutive frames."""

    current: int
    """The current frame number."""

    _callback: Optional[Callable[[FrameProgressReport], None]] = None
    """Callback to call in every iteration to report progress."""

    _callback_called_at: float
    """Time when the callback was last called."""

    _progress: FrameProgressReport
    """Frame progress report object yielded from the callback."""

    def __init__(
        self,
        start: int,
        end: int,
        step: int,
        *,
        operation: Optional[str] = None,
        progress: Optional[Callable[[FrameProgressReport], None]] = None,
    ):
        self.start = start
        self.end = max(start, end)
        self.step = step
        self.current = start

        total_steps, remainder = divmod(self.end - self.start, self.step)
        total_steps += 2 if remainder else 1

        self._progress = FrameProgressReport(
            frame_range=(start, end), operation=operation, total_steps=total_steps
        )
        self._callback = progress
        self._callback_called_at = 0

    def __iter__(self) -> Iterator[int]:
        return self

    def __next__(self) -> int:
        if self.current > self.end:
            self._progress.total_steps = self._progress.steps_done
            if self._callback:
                self._callback(self._progress)
            raise StopIteration

        if self.current == self.end:
            frame = self.end
            self.current += self.step
            return self.end
        else:
            frame = self.current
            self.current = min(self.current + self.step, self.end)

        self._progress.current_frame = frame
        self._progress.steps_done += 1

        if self._callback:
            now = time()

            if not self._progress.start_time:
                self._progress.start_time = now
            self._progress.current_time = now

            if now - self._callback_called_at >= 1 or frame == self.end:
                self._callback(self._progress)
                self._callback_called_at = now

        return frame
