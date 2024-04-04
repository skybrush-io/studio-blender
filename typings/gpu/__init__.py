from typing import Protocol

from .types import GPUShader


class _Shader(Protocol):
    def from_builtin(self, shader_name: str, config: str = "DEFAULT") -> GPUShader: ...


shader: _Shader
