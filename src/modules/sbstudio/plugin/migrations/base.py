from abc import ABC, abstractmethod
from logging import Logger
from typing import ClassVar

from bpy.types import Context


class Migration(ABC):
    """Base class for file format migrations."""

    label: str
    """A human-readable label for the migration."""

    description: str
    """A short description of the migration."""

    version_range: ClassVar[tuple[int, int]]
    """The version range (from, to) for the migration.

    The migration should be applied if the current file version is
    equal to `from`. The migration will update the file version to `to`.
    """

    @classmethod
    @abstractmethod
    def needs_migration(cls, context: Context) -> bool:
        """Returns whether the current file needs migration.

        This function should return a response based on actually evaluating the
        content of the file, not just the version number. Version number checks are
        assumed to have been done by teh caller.
        """
        ...

    @abstractmethod
    def execute(self, context: Context, *, log: Logger) -> None:
        """Executes the migration on the given context.

        This function should be called only when the file actually needs migration.
        It is assumed to have been checked by the caller.
        """
        ...
