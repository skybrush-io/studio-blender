"""Throttled validation progress with explicit cancellation checkpoints."""

from time import monotonic

from sbstudio.plugin.errors import TaskCancelled

from .progress import StepBasedProgressReport


def validation_progress_callback(handler):
    stage = None
    last_update = float("-inf")
    report = None
    previous = 0

    def update(name, done, total):
        nonlocal stage, last_update, report, previous
        changed = name != stage
        if changed:
            stage = name
            previous = 0
            report = StepBasedProgressReport(total, operation=name)
            report.start(name)
        assert report is not None
        report.add_steps(done - previous)
        previous = done
        now = monotonic()
        if changed or done == total or now - last_update >= 0.25:
            last_update = now
            if handler(report):
                raise TaskCancelled(f"Cancelled operation: {name}")

    return update
