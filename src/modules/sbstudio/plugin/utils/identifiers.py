__all__ = ("create_internal_id",)


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
