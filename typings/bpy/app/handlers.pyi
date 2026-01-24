from typing import Callable, Generic, Iterable, ParamSpec, TypeVar

from bpy.types import Depsgraph, Scene

P = ParamSpec("P")
T = TypeVar("T")

Func = TypeVar("Func", bound=Callable[..., None])

class HandlerList(Generic[Func]):
    def append(self, func: Func) -> None: ...
    def remove(self, func: Func) -> None: ...
    def __iter__(self) -> Iterable[Func]: ...

depsgraph_update_post: HandlerList[Callable[[Scene, Depsgraph], None]]
frame_change_post: HandlerList[Callable[[Scene, Depsgraph], None]]
load_post: HandlerList[Callable[[str], None]]

def persistent(func: Callable[P, T]) -> Callable[P, T]: ...
