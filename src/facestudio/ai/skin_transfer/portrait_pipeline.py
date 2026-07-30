from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QSize

from facestudio.ai.skin_transfer.alignment import LandmarkDetector, align_portrait, read_image
from facestudio.ai.skin_transfer.pipeline import SkinTransferPipeline, SkinTransferRequest, SkinTransferResult


@dataclass(frozen=True)
class PortraitSkinTransferRequest:
    portrait: Path
    donor_texture: Path
    output: Path
    detector: LandmarkDetector
    diagnostics_dir: Path | None = None
    aligned_preview: Path | None = None
    colour_strength: float = 0.85


class PortraitSkinTransferPipeline:
    """Align a normal portrait, then run the UV-safe surface-transfer stage."""

    name = "portrait-skin-transfer-v1"

    def __init__(self, transfer: SkinTransferPipeline | None = None) -> None:
        self.transfer = transfer or SkinTransferPipeline()

    def run(self, request: PortraitSkinTransferRequest) -> SkinTransferResult:
        portrait = read_image(request.portrait)
        donor = read_image(request.donor_texture)
        alignment = align_portrait(portrait, request.detector, QSize(donor.width(), donor.height()))

        aligned_path = request.aligned_preview or request.output.with_name(f"{request.output.stem}_aligned.png")
        aligned_path = aligned_path.expanduser().resolve()
        aligned_path.parent.mkdir(parents=True, exist_ok=True)
        if not alignment.image.save(str(aligned_path), "PNG"):
            raise RuntimeError(f"Could not save aligned portrait preview: {aligned_path}")

        result = self.transfer.run(
            SkinTransferRequest(
                aligned_portrait=aligned_path,
                donor_texture=request.donor_texture,
                output=request.output,
                diagnostics_dir=request.diagnostics_dir,
                colour_strength=request.colour_strength,
            )
        )
        metadata = dict(result.metadata)
        metadata.update(
            {
                "portrait_alignment": self.name,
                "landmark_detector": alignment.detector,
                "aligned_preview": str(aligned_path),
                "donor_geometry_preserved": True,
            }
        )
        return SkinTransferResult(result.output, result.diagnostics, metadata)
