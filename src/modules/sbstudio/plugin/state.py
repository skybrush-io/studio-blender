"""Global and file-specific state of the Skybrush Studio plugin."""

import bpy
import json

from abc import ABCMeta, abstractmethod
from bpy.app.handlers import persistent
from typing import Any, Dict

from .utils import (
    create_internal_id,
    ensure_object_exists_in_collection,
    get_object_in_collection,
)


class StateBase(metaclass=ABCMeta):
    """Superclass for state objects that can be saved to and loaded from
    Blender text blocks.
    """

    @abstractmethod
    def from_json(self, data: Dict[str, Any]) -> None:
        """Updates the current state object from the data retrieved from a state
        object saved earlier with `to_json()`.
        """
        raise NotImplementedError

    def reset(self) -> None:
        """Resets the current state object to its defaults."""
        pass

    @abstractmethod
    def to_json(self) -> Dict[str, Any]:
        """Returns a representation of the state object that can be stored in a
        JSON object.
        """
        raise NotImplementedError


class _SkybrushStudioFileState:
    """Class representing the state of a single .blend file loaded into the
    Skybrush Studio Blender plugin.
    """

    _initialized: bool = False

    def from_json(self, data: Dict[str, Any]) -> None:
        self._initialized = bool(data.get("initialized", False))

    def reset(self) -> None:
        self._initialized = False

    def to_json(self) -> Dict[str, Any]:
        """Returns a representation of the state object that can be stored in
        JSON.
        """
        return {"initialized": self._initialized}

    def ensure_initialized(self) -> None:
        """Initializes the plugin in the current file if it has not been
        initialized yet.
        """
        if not self._initialized:
            self._initialize()
            self._initialized = True

    def _initialize(self) -> None:
        """Initializes the plugin in the current file, assuming that it is not
        initialized yet.
        """
        pass


#: File-specific state object
_file_specific_state = _SkybrushStudioFileState()


def get_file_specific_state() -> _SkybrushStudioFileState:
    """Returns the file-specific state of the Skybrush Studio plugin."""
    return _file_specific_state


def _load(key: str, state: StateBase) -> None:
    """Restores a state object from a text block in the current Blender file."""
    key = "." + create_internal_id(key)
    try:
        block = get_object_in_collection(bpy.data.texts, key)
    except KeyError:
        block = None
    if block:
        data = json.loads(block.as_string())
        state.from_json(data)


def _save(key: str, state: StateBase) -> None:
    """Saves a state object in the current Blender file as a text block."""
    data = json.dumps(state.to_json())

    key = "." + create_internal_id(key)
    block = ensure_object_exists_in_collection(bpy.data.texts, key)
    block.from_string(data)


@persistent
def _load_file_specific_state(_dummy):
    _file_specific_state.reset()
    _load("State", _file_specific_state)


@persistent
def _save_file_specific_state(_dummy):
    _save("State", _file_specific_state)


def register() -> None:
    """Registers the state handlers responsible for saving the file-specific
    state before the file is saved and loading them back when the file is
    loaded.
    """
    if _load_file_specific_state not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_load_file_specific_state)
    if _save_file_specific_state not in bpy.app.handlers.save_pre:
        bpy.app.handlers.save_pre.append(_save_file_specific_state)


def unregister() -> None:
    """Unregisters the state handlers responsible for saving the file-specific
    state before the file is saved and loading them back when the file is
    loaded.
    """
    if _save_file_specific_state in bpy.app.handlers.save_pre:
        bpy.app.handlers.save_pre.remove(_save_file_specific_state)
    if _load_file_specific_state in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_load_file_specific_state)
