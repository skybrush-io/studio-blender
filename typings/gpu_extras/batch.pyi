from typing import Any, Literal

from gpu.types import GPUBatch, GPUShader

def batch_for_shader(
    shader: GPUShader,
    type: Literal["POINTS"]
    | Literal["LINES"]
    | Literal["LINE_STRIP"]
    | Literal["TRIS"]
    | Literal["LINES_ADJ"],
    content: dict[str, Any],
    *,
    indices=None,
) -> GPUBatch: ...
