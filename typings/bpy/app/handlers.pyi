from typing import Callable, ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")

def persistent(func: Callable[P, T]) -> Callable[P, T]: ...
