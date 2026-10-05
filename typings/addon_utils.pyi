from types import ModuleType

def enable(
    module_name: str,
    *,
    default_set: bool = False,
    persistent: bool = False,
    handle_error=None,
) -> ModuleType | None: ...
