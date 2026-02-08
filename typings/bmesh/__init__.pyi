from bmesh import ops

from .types import BMesh

__all__ = ("new", "ops")

def new(use_operators: bool = True) -> BMesh: ...
