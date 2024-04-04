from typing import Any, Dict, Literal, Union

from gpu.types import GPUBatch, GPUShader

def batch_for_shader(
    shader: GPUShader,
    type: Union[
        Literal["POINTS"],
        Literal["LINES"],
        Literal["LINE_STRIP"],
        Literal["TRIS"],
        Literal["LINES_ADJ"],
    ],
    content: Dict[str, Any],
    *,
    indices=None
) -> GPUBatch: ...
