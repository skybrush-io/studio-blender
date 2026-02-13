from bmesh.types import BMEdgeSeq, BMesh
from mathutils import Matrix

def create_cone(
    bm: BMesh,
    cap_ends: bool = False,
    cap_tris: bool = False,
    segments: int = 0,
    radius1: float = 0,
    radius2: float = 0,
    depth: float = 0,
    matrix: Matrix | None = None,
    calc_uvs: bool = False,
) -> None: ...
def create_icosphere(
    bm: BMesh,
    subdivisions: int = 0,
    radius: float = 0,
    matrix: Matrix | None = None,
    calc_uvs: bool = False,
) -> None: ...
def subdivide_edges(
    bm: BMesh,
    edges: BMEdgeSeq,
    smooth: float = 0,
    cuts: int = 0,
    use_grid_fill: bool = False,
) -> None: ...
