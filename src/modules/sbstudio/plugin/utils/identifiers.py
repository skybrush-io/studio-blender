import bpy

from itertools import count as count_from

__all__ = ("create_internal_id", "is_internal_id", "propose_name", "propose_names")


def create_internal_id(name: str) -> str:
    """Creates an internal identifier that we can use to identify objects
    that we have created in Blender.

    Parameters:
        name: the name of the object being created. It will be wrapped in
            `Skybrush[...]` so we can find all the internal objects we have
            created later.

    Returns:
        the generated ID; currently it is the input name wrapped in
        `Skybrush[...]`
    """
    return f"Skybrush[{name}]"


def is_internal_id(name: str) -> bool:
    """Returns whether the given ID looks like one that was generated from
    `create_internal_id()`.
    """
    return name.startswith("Skybrush[") and name.endswith("]")


def propose_name(template: str, *, for_collection: bool = False) -> str:
    """Proposes a name for an object such that its name is similar to the given
    template. The template should include a marker (`{}`) that is replaced with
    the smallest integer starting from 1 that is not taken yet.

    Parameters:
        for_collection: whether the name should be for a new collection or for
            a new object; in Blender, these live in different namespaces.

    Returns:
        the proposed name for a new object
    """
    return propose_names(template, 1, for_collection=for_collection)[0]


def propose_names(
    template: str, count: int, *, for_collection: bool = False
) -> list[str]:
    """Proposes new names for a given number of objects such that the names of
    the objects are similar to the given template. The template should include a
    marker (`{}`) that is replaced with consecutive integers starting from 1.

    Parameters:
        for_collection: whether the name should be for a new collection or for
            a new object; in Blender, these live in different namespaces.

    Returns:
        the proposed names for the given number of objects
    """
    if count <= 0:
        return []

    coll = bpy.data.collections if for_collection else bpy.data.objects
    result = []

    if "{}" not in template:
        # Try the "naked" name first
        try:
            coll[template]
        except KeyError:
            # Okay, the "naked" template is not taken yet
            result.append(template)

        template = template + " {}"

    if len(result) < count:
        for index in count_from(1):
            candidate = template.format(index)
            try:
                coll[candidate]
            except KeyError:
                # Okay, the "naked" template is not taken yet
                result.append(candidate)
                if len(result) >= count:
                    break

    return result
