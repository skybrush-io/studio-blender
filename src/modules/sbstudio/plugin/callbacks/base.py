from __future__ import annotations

from collections.abc import Callable, Sequence
from functools import partial
from typing import Generic, ParamSpec, overload

P = ParamSpec("P")

Disposer = Callable[[], None]


class CallbackList(Generic[P], Sequence[Callable[P, None]]):
    """A list of callbacks that can be called with the same positional and keyword
    arguments.
    """

    _items: list[Callable[P, None]]

    def __init__(self) -> None:
        self._items = []

    def append(self, callback: Callable[P, None]) -> Disposer:
        """Appends a callback to the end of the callback list.

        Returns:
            a disposer function that can be called with no arguments to remove the
            callback from the list.
        """
        self._items.append(callback)
        return partial(self.remove, callback)

    def ensure(self, callback: Callable[P, None], *, present: bool = True) -> bool:
        """Ensures that a callback is in the callback list or it is _not_ in the
        callback list, depending on the value of the `present` argument.

        If `present` is `True` and the callback is not already in the list, it is
        appended to the end of the list.

        If `present` is `False` and the callback is in the list, it is removed from the
        list.

        Returns:
            whether the callback list changed during the call
        """
        if present:
            if callback not in self._items:
                self._items.append(callback)
                return True
        else:
            if callback in self._items:
                self._items.remove(callback)
                return True

        return False

    def ensure_missing(self, callback: Callable[P, None]) -> bool:
        """Ensures that a callback is not in the callback list.

        Alias for `ensure(..., present=False)` but has better readability in certain
        contexts.

        Returns:
            whether the callback was removed from the list during the call
        """
        return self.ensure(callback, present=False)

    def prepend(self, callback: Callable[P, None]) -> Disposer:
        """Prepends a callback to the beginning of the callback list.

        Returns:
            a disposer function that can be called with no arguments to remove the
            callback from the list.
        """
        self._items.insert(0, callback)
        return partial(self.remove, callback)

    def remove(self, callback: Callable[P, None]) -> None:
        """Remove a callback from the list."""
        self._items.remove(callback)

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> None:
        """Call all callbacks in the list with the given arguments."""
        for callback in self._items:
            callback(*args, **kwargs)

    @overload
    def __getitem__(self, index: int) -> Callable[P, None]: ...
    @overload
    def __getitem__(self, index: slice) -> Sequence[Callable[P, None]]: ...
    def __getitem__(self, index: int | slice):
        return self._items[index]

    def __len__(self) -> int:
        return len(self._items)
