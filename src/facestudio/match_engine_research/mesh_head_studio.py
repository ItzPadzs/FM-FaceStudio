from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtGui import QImage, QImageReader

from facestudio.match_engine_research.auto_texture import AutoTextureAssistant, AutoTextureResult
from facestudio.match_engine_research.photo_to_3d import Photo3DResult, PhotoTo3DService


@dataclass(frozen=True)
class PhotoAssessment:
    width: int
    height: int
    aspect_ratio: float
    quality: str
    notes: tuple[str, ...]


@dataclass(frozen=True)
class MeshSourceAssessment:
    source_path: str | None
    source_type: str
    usable_for_preview: bool
    notes: tuple[str, ...]


class MeshHeadStudioService:
    """Orchestrate the existing FaceStudio photo, texture and mesh research tools.

    Alpha 6 presents one coherent workflow. It can analyse a portrait, create the
    strongest currently available local head-style preview, inspect a user-selected
    mesh source, and transfer the portrait into an observed FM26 UV layout.

    It does not claim that an FM26 ``.skin`` file has been decoded into an editable
    mesh. A user-supplied OBJ is recognised as a preview source, while ``.skin`` is
    treated as research evidence only until its geometry and UV structure are proven.
    """

    def __init__(self) -> None:
        self.photo_service = PhotoTo3DService()
        self.texture_assistant = AutoTextureAssistant()

    def assess_photo(self, photo_path: Path) -> PhotoAssessment:
        image = self._read(photo_path)
        if image.isNull():
            raise ValueError("The selected photograph could not be decoded.")
        width, height = image.width(), image.height()
        ratio = width / max(1, height)
        notes: list[str] = []
        if min(width, height) < 512:
            notes.append("Use a higher-resolution portrait for cleaner texture detail.")
        if ratio > 1.15:
            notes.append("A portrait-orientation or square image will align more reliably.")
        if ratio < 0.55:
            notes.append("The image is very narrow; include both ears where possible.")
        quality = "Good" if min(width, height) >= 768 and 0.55 <= ratio <= 1.15 else "Usable"
        return PhotoAssessment(width, height, round(ratio, 3), quality, tuple(notes))

    def assess_mesh_source(self, path: Path | None) -> MeshSourceAssessment:
        if path is None:
            return MeshSourceAssessment(None, "No mesh selected", False, ("Select a user-supplied OBJ for mesh preview, or a SKIN file for research inspection.",))
        path = path.expanduser().resolve()
        if not path.is_file():
            raise ValueError("The selected mesh source does not exist.")
        suffix = path.suffix.lower()
        if suffix == ".obj":
            return MeshSourceAssessment(str(path), "Wavefront OBJ", True, ("OBJ can be used as an external preview mesh.", "FaceStudio does not assume it matches FM26 topology unless verified."))
        if suffix == ".skin":
            return MeshSourceAssessment(str(path), "FM26 SKIN research file", False, ("The SKIN file can be fingerprinted and compared.", "Its mesh and UV structure are not yet decoded, so it cannot be rendered honestly."))
        return MeshSourceAssessment(str(path), f"Unsupported {suffix or 'file'}", False, ("Use OBJ for a preview mesh or SKIN for research inspection.",))

    def build_head_preview(self, photo_path: Path, yaw: int = 0, depth_strength: int = 58) -> Photo3DResult:
        return self.photo_service.create_preview(photo_path, yaw=yaw, depth_strength=depth_strength, size=560)

    def bake_to_template(self, player_id: str, photo_path: Path, template_path: Path) -> AutoTextureResult:
        return self.texture_assistant.generate(player_id, photo_path, template_path)

    @staticmethod
    def _read(path: Path) -> QImage:
        if not path.is_file():
            raise ValueError(f"Image not found: {path}")
        reader = QImageReader(str(path))
        reader.setAutoTransform(True)
        return reader.read()
