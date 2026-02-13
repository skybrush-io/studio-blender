from typing import Type

from bpy.types import (
    AddonPreferences,
    Header,
    Menu,
    Node,
    NodeSocket,
    NodeTree,
    Operator,
    Panel,
    PropertyGroup,
    UIList,
)

def register_class(
    cls: Type[
        Panel
        | UIList
        | Menu
        | Header
        | Operator
        | PropertyGroup
        | AddonPreferences
        | NodeTree
        | Node
        | NodeSocket
    ],
) -> None: ...
def unregister_class(
    cls: Type[
        Panel
        | UIList
        | Menu
        | Header
        | Operator
        | PropertyGroup
        | AddonPreferences
        | NodeTree
        | Node
        | NodeSocket
    ],
) -> None: ...
