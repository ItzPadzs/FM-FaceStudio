"""Mesh-loading boundary.

Sprint 4 supports Wavefront OBJ files only. Football Manager `.skin` and
other proprietary formats remain unsupported until their structures are
validated independently.
"""

from facestudio.mesh.inspection import BinaryInspection, inspect_binary
from facestudio.mesh.model import MeshData, Vec3
from facestudio.mesh.obj_loader import ObjFormatError, load_obj

__all__ = [
    "BinaryInspection",
    "MeshData",
    "ObjFormatError",
    "Vec3",
    "inspect_binary",
    "load_obj",
]
