from typing import Callable

def register(
    func: Callable[[], float | None],
    first_interval: float = 0,
    persistent: bool = False,
) -> None: ...
def unregister(func: Callable[[], float | None]) -> None: ...
