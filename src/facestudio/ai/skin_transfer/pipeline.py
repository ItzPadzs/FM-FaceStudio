from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QImageReader

from facestudio.ai.skin_transfer.candidate import extract_skin_candidate
from facestudio.ai.skin_transfer.colour_match import apply_colour_shift, compute_colour_shift
from facestudio.ai.skin_transfer.compositor import composite
from facestudio.ai.skin_transfer.confidence import combine_confidence
from facestudio.ai.skin_transfer.diagnostics import save_diagnostics
from facestudio.ai.skin_transfer.masks import build_protection_mask


@dataclass(frozen=True)
class SkinTransferRequest:
    aligned_portrait: Path
    donor_texture: Path
    output: Path
    diagnostics_dir: Path | None = None
    colour_strength: float = 0.85


@dataclass(frozen=True)
class SkinTransferResult:
    output: Path
    diagnostics: tuple[Path, ...]
    metadata: dict[str, object]


class SkinTransferPipeline:
    """Bootstrap UV-safe transfer pipeline for aligned portrait and donor images."""

    name = "skin-transfer-prototype-v1"

    @staticmethod
    def _read(path: Path) -> QImage:
        reader = QImageReader(str(path))
        reader.setAutoTransform(True)
        image = reader.read()
        if image.isNull():
            raise ValueError(f"Could not read image {path}: {reader.errorString()}")
        return image.convertToFormat(QImage.Format.Format_RGB32)

    def run(self, request: SkinTransferRequest) -> SkinTransferResult:
        portrait = self._read(request.aligned_portrait)
        donor = self._read(request.donor_texture)
        if portrait.size() != donor.size():
            portrait = portrait.scaled(
                donor.size(),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

        candidate = extract_skin_candidate(portrait)
        protection = build_protection_mask(donor.size())
        confidence = combine_confidence(candidate.mask, protection)
        shift = compute_colour_shift(candidate.image, donor, confidence)
        matched = apply_colour_shift(candidate.image, shift, request.colour_strength)
        final = composite(matched, donor, confidence)

        output = request.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        if not final.save(str(output), "PNG"):
            raise RuntimeError(f"Could not save skin-transfer output: {output}")

        diagnostics: tuple[Path, ...] = ()
        if request.diagnostics_dir is not None:
            diagnostics = save_diagnostics(
                request.diagnostics_dir,
                {
                    "skin_candidate": candidate.image,
                    "candidate_mask": candidate.mask,
                    "protection_mask": protection,
                    "confidence_map": confidence,
                    "colour_matched": matched,
                    "composite_preview": final,
                },
            )

        return SkinTransferResult(
            output=output,
            diagnostics=diagnostics,
            metadata={
                "engine": self.name,
                "geometry_warped": False,
                "protected_regions": ["eyes", "nostrils", "mouth", "ears"],
                "colour_shift_rgb": [shift.red, shift.green, shift.blue],
                "output_size": [final.width(), final.height()],
            },
        )
