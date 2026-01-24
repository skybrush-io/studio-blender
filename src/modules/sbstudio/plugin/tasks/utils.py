from contextlib import contextmanager
from functools import wraps
from typing import Callable, ParamSpec

__all__ = ("Suspension",)

P = ParamSpec("P")


class Suspension:
    """Adds support for suspending a task in a reentrant manner.

    This class maintains a counter that can be incremented and decremented.
    When the counter is greater than zero, the task is considered suspended.
    When the counter reaches zero, the task is resumed.

    It is advised not to manipulate the counter directly, but to use the
    context manager interface provided by this class.
    """

    _counter: int

    def __init__(self):
        self._counter = 0

    @contextmanager
    def use(self):
        """Context manager that suspends the task while inside the context.

        Usage:
            with suspension.use():
                # Task is suspended here
                ...
            # Task is resumed here
        """
        self._counter += 1
        try:
            yield
        finally:
            self._counter -= 1

    def wrap(self, func: Callable[P, None]) -> Callable[P, None]:
        """Decorator that wraps a function so that it is not executed while
        the task is suspended.

        Usage:
            @suspension.wrap
            def my_function(...):
                ...
        """

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> None:
            if self._counter <= 0:
                return func(*args, **kwargs)

        return wrapper
