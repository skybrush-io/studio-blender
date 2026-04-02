from functools import wraps
from time import monotonic

import bpy

__all__ = ("debounced",)


def debounced(delay):
    """Decorator factory that creates a decorator that debounces the execution
    of a single-arg function with the given delay.
    """

    def decorator(func):
        """Decorator that can be applied to the given single-arg function to
        produce a debounced variant.
        """

        _timer_registered = False
        _last_interaction_at = None
        _last_args = None
        _last_kwds = None

        def has_interaction_ended_timer():
            nonlocal _last_interaction_at, _last_args, _last_kwds, _timer_registered

            if monotonic() - _last_interaction_at > delay:
                # No interaction any more, time to call the function
                func(*_last_args, **_last_kwds)

                _timer_registered = False
                _last_interaction_at = None
                _last_args = None
                _last_kwds = None

                return None
            else:
                # Interaction still ongoing, check back soon
                return delay / 2

        @wraps(func)
        def debounced(*args, **kwds):
            """Schedules a safety check to be executed soon in the current scene. Takes
            care of collapsing multiple invocations in quick succession into a single
            safety check to ensure we do not do needless validations when the user is
            interacting with the scene.
            """
            nonlocal _last_interaction_at, _last_args, _last_kwds, _timer_registered

            _last_interaction_at = monotonic()
            _last_args = args
            _last_kwds = kwds

            if not _timer_registered:
                _timer_registered = True
                bpy.app.timers.register(has_interaction_ended_timer)

        debounced.now = func

        return debounced

    return decorator
