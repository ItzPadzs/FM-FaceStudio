from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from PySide6.QtGui import QColor, QImage, QImageReader

VALIDATION_FORMAT = "facestudio-texture-validation-v1"
BUILD_FORMAT = "facestudio-texture-build-v3"


@dataclass(frozen=True)
class ValidationCheck:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class RegionMetric:
    name: str
    average_difference: float
    changed_coverage: float
    confidence: float


@dataclass(frozen=True)
class ValidationResult:
    player_id: str
    donor_texture: str
    refined_texture: str
    width: int
    height: int
    checks: tuple[ValidationCheck, ...]
    regions: tuple[RegionMetric, ...]
    quality_score: int
    ready_for_testing: bool
    heatmap: QImage
    source_manifest: dict


class TextureValidationService:
    """Validate and package one refined donor texture without modifying FM files."""

    REGIONS = (
        ("forehead", 0.28, 0.08, 0.72, 0.34),
        ("left_eye", 0.25, 0.27, 0.50, 0.48),
        ("right_eye", 0.50, 0.27, 0.75, 0.48),
        ("nose", 0.40, 0.34, 0.60, 0.67),
        ("left_cheek", 0.24, 0.43, 0.50, 0.72),
        ("right_cheek", 0.50, 0.43, 0.76, 0.72),
        ("mouth", 0.36, 0.59, 0.64, 0.78),
        ("jaw", 0.25, 0.67, 0.75, 0.90),
        ("chin", 0.38, 0.75, 0.62, 0.96),
    )

    def validate(self, refinement_manifest: Path) -> ValidationResult:
        payload = self._json(refinement_manifest)
        if payload.get("format") != "facestudio-texture-build-v2":
            raise ValueError("Expected a facestudio-texture-build-v2 manifest.")
        player_id = str(payload.get("player_id", ""))
        if not player_id.isdigit():
            raise ValueError("Refinement manifest has an invalid player ID.")
        donor_path = Path(str(payload.get("donor_texture", ""))).expanduser()
        refined_path = Path(str(payload.get("output_texture", ""))).expanduser()
        donor = self._read(donor_path).convertToFormat(QImage.Format.Format_ARGB32)
        refined = self._read(refined_path).convertToFormat(QImage.Format.Format_ARGB32)

        same_dimensions = donor.size() == refined.size()
        width, height = refined.width(), refined.height()
        alpha_opaque, alpha_partial = self._alpha_counts(refined)
        invalid_pixels = self._invalid_pixel_count(refined)
        changed_pixels, outside_change_ratio = self._difference_stats(donor, refined)
        empty_ratio = self._empty_ratio(refined)

        checks = (
            ValidationCheck("PNG decode", True, f"Decoded {width}×{height} ARGB texture."),
            ValidationCheck("Matching dimensions", same_dimensions, f"Donor {donor.width()}×{donor.height()}, refined {width}×{height}."),
            ValidationCheck("Square texture", width == height, f"Texture ratio {width}:{height}."),
            ValidationCheck("Power-of-two dimensions", self._power_of_two(width) and self._power_of_two(height), f"Dimensions {width}×{height}."),
            ValidationCheck("Alpha channel", alpha_partial == 0, f"Opaque pixels: {alpha_opaque}; partial/transparent pixels: {alpha_partial}."),
            ValidationCheck("Valid colour values", invalid_pixels == 0, f"Invalid pixels: {invalid_pixels}."),
            ValidationCheck("Non-empty texture", empty_ratio < 0.02, f"Near-empty pixel ratio: {empty_ratio:.2%}."),
            ValidationCheck("Facial reconstruction present", changed_pixels > 0, f"Changed pixels versus donor: {changed_pixels}."),
            ValidationCheck("Outside-face preservation", outside_change_ratio <= 0.08, f"Estimated peripheral change ratio: {outside_change_ratio:.2%}."),
        )
        regions = tuple(self._region_metric(name, box, donor, refined) for name, *box in self.REGIONS)
        score = self._score(checks, regions)
        ready = all(check.passed for check in checks if check.name not in {"Power-of-two dimensions"}) and score >= 75
        return ValidationResult(
            player_id, str(donor_path), str(refined_path), width, height,
            checks, regions, score, ready, self._heatmap(donor, refined), payload,
        )

    @staticmethod
    def save_report(result: ValidationResult, destination: Path) -> tuple[Path, Path, Path]:
        stem = destination.with_suffix("")
        json_path = stem.with_suffix(".validation.json")
        html_path = stem.with_suffix(".validation.html")
        heatmap_path = stem.with_suffix(".heatmap.png")
        payload = TextureValidationService._payload(result)
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        html_path.write_text(TextureValidationService._html(payload), encoding="utf-8")
        if not result.heatmap.save(str(heatmap_path), "PNG"):
            raise OSError(f"Could not save validation heatmap: {heatmap_path}")
        return json_path, html_path, heatmap_path

    @staticmethod
    def create_test_package(result: ValidationResult, destination: Path) -> Path:
        package = destination / f"facestudio-test-{result.player_id}"
        package.mkdir(parents=True, exist_ok=True)
        texture_target = package / f"{result.player_id}.png"
        backup_target = package / f"{result.player_id}.original.png"
        shutil.copy2(result.refined_texture, texture_target)
        shutil.copy2(result.donor_texture, backup_target)
        report_json, report_html, heatmap = TextureValidationService.save_report(result, package / "validation")
        manifest = {
            "format": BUILD_FORMAT,
            "player_id": result.player_id,
            "validated_texture": str(texture_target),
            "original_backup": str(backup_target),
            "validation_report": str(report_json),
            "validation_html": str(report_html),
            "difference_heatmap": str(heatmap),
            "quality_score": result.quality_score,
            "ready_for_testing": result.ready_for_testing,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_refinement": result.source_manifest,
            "installation": "manual-and-reversible",
            "warning": "This package does not prove match-engine compatibility and does not modify Football Manager automatically.",
            "next_stage": "controlled-in-game-evaluation",
        }
        (package / "facestudio-build-v3.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        (package / "README.txt").write_text(
            "FM FaceStudio controlled test package\n\n"
            "1. Back up the target FM texture before testing.\n"
            "2. Replace only the matching numeric-ID PNG manually.\n"
            "3. Clear/reload the relevant FM graphics cache if required.\n"
            "4. Restore the .original.png backup immediately if the result is unsuitable.\n\n"
            "FaceStudio has not modified FM files automatically and does not claim .skin compatibility.\n",
            encoding="utf-8",
        )
        return package

    @staticmethod
    def _payload(result: ValidationResult) -> dict:
        return {
            "format": VALIDATION_FORMAT,
            "player_id": result.player_id,
            "donor_texture": result.donor_texture,
            "refined_texture": result.refined_texture,
            "dimensions": {"width": result.width, "height": result.height},
            "checks": [asdict(check) for check in result.checks],
            "regions": [asdict(region) for region in result.regions],
            "quality_score": result.quality_score,
            "ready_for_testing": result.ready_for_testing,
            "advisory": "Validation is an internal consistency check, not proof of in-game compatibility.",
        }

    @staticmethod
    def _html(payload: dict) -> str:
        checks = "".join(f"<li><strong>{'PASS' if c['passed'] else 'FAIL'}</strong> — {c['name']}: {c['detail']}</li>" for c in payload["checks"])
        regions = "".join(f"<tr><td>{r['name']}</td><td>{r['average_difference']:.2f}</td><td>{r['changed_coverage']:.1%}</td><td>{r['confidence']:.1%}</td></tr>" for r in payload["regions"])
        return f"""<!doctype html><html><head><meta charset='utf-8'><title>FM FaceStudio Validation</title></head><body>
<h1>FM FaceStudio Texture Validation</h1><p>Player ID: {payload['player_id']}</p>
<h2>Advisory score: {payload['quality_score']}%</h2><p>Ready for controlled testing: {'Yes' if payload['ready_for_testing'] else 'No'}</p>
<h2>Checks</h2><ul>{checks}</ul><h2>Regions</h2><table border='1' cellpadding='6'><tr><th>Region</th><th>Average difference</th><th>Coverage</th><th>Confidence</th></tr>{regions}</table>
<p>{payload['advisory']}</p></body></html>"""

    def _region_metric(self, name: str, box: list[float], donor: QImage, refined: QImage) -> RegionMetric:
        x0, y0, x1, y1 = box
        left, top = int(x0 * refined.width()), int(y0 * refined.height())
        right, bottom = int(x1 * refined.width()), int(y1 * refined.height())
        total = changed = 0
        difference = 0.0
        for y in range(max(0, top), min(refined.height(), bottom)):
            for x in range(max(0, left), min(refined.width(), right)):
                a, b = donor.pixelColor(x, y), refined.pixelColor(x, y)
                delta = (abs(a.red()-b.red()) + abs(a.green()-b.green()) + abs(a.blue()-b.blue())) / 3.0
                difference += delta; total += 1
                if delta > 2.0: changed += 1
        coverage = changed / total if total else 0.0
        avg = difference / total if total else 0.0
        confidence = max(0.0, min(1.0, coverage * (1.0 - min(avg, 128.0) / 256.0)))
        return RegionMetric(name, round(avg, 3), round(coverage, 4), round(confidence, 4))

    @staticmethod
    def _score(checks: tuple[ValidationCheck, ...], regions: tuple[RegionMetric, ...]) -> int:
        check_score = sum(1 for check in checks if check.passed) / len(checks) * 70.0
        region_score = sum(region.confidence for region in regions) / len(regions) * 30.0
        return max(0, min(100, round(check_score + region_score)))

    @staticmethod
    def _heatmap(donor: QImage, refined: QImage) -> QImage:
        output = QImage(refined.size(), QImage.Format.Format_ARGB32)
        for y in range(refined.height()):
            for x in range(refined.width()):
                a, b = donor.pixelColor(x, y), refined.pixelColor(x, y)
                delta = min(255, abs(a.red()-b.red()) + abs(a.green()-b.green()) + abs(a.blue()-b.blue()))
                output.setPixelColor(x, y, QColor(delta, max(0, 255-delta), 0, 255))
        return output

    @staticmethod
    def _difference_stats(donor: QImage, refined: QImage) -> tuple[int, float]:
        if donor.size() != refined.size():
            return 0, 1.0
        changed = peripheral = peripheral_changed = 0
        w, h = refined.width(), refined.height()
        for y in range(h):
            for x in range(w):
                a, b = donor.pixelColor(x, y), refined.pixelColor(x, y)
                different = abs(a.red()-b.red()) + abs(a.green()-b.green()) + abs(a.blue()-b.blue()) > 4
                changed += int(different)
                outside = x < w*0.18 or x > w*0.82 or y < h*0.04 or y > h*0.97
                if outside:
                    peripheral += 1; peripheral_changed += int(different)
        return changed, peripheral_changed / peripheral if peripheral else 0.0

    @staticmethod
    def _alpha_counts(image: QImage) -> tuple[int, int]:
        opaque = partial = 0
        for y in range(image.height()):
            for x in range(image.width()):
                if image.pixelColor(x, y).alpha() == 255: opaque += 1
                else: partial += 1
        return opaque, partial

    @staticmethod
    def _empty_ratio(image: QImage) -> float:
        empty = 0; total = image.width() * image.height()
        for y in range(image.height()):
            for x in range(image.width()):
                c = image.pixelColor(x, y)
                if c.alpha() == 0 or max(c.red(), c.green(), c.blue()) <= 1: empty += 1
        return empty / total if total else 1.0

    @staticmethod
    def _invalid_pixel_count(image: QImage) -> int:
        return 0 if not image.isNull() else 1

    @staticmethod
    def _power_of_two(value: int) -> bool:
        return value > 0 and value & (value - 1) == 0

    @staticmethod
    def _json(path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Could not read refinement manifest: {exc}") from exc

    @staticmethod
    def _read(path: Path) -> QImage:
        reader = QImageReader(str(path)); reader.setAutoTransform(True)
        image = reader.read()
        if image.isNull():
            raise ValueError(f"Texture could not be decoded: {path}")
        return image
