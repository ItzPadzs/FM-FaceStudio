from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from PySide6.QtGui import QColor, QImage, QImageReader

REFINEMENT_FORMAT = "facestudio-texture-build-v2"


@dataclass(frozen=True)
class RefinementSettings:
    feather_radius: int = 6
    colour_matching: float = 0.65
    neighbour_blend: float = 0.35

    def normalised(self) -> "RefinementSettings":
        return RefinementSettings(
            max(0, min(20, int(self.feather_radius))),
            max(0.0, min(1.0, float(self.colour_matching))),
            max(0.0, min(1.0, float(self.neighbour_blend))),
        )


@dataclass(frozen=True)
class RefinementResult:
    player_id: str
    donor_texture: str
    raw_texture: str
    output: QImage
    settings: RefinementSettings
    changed_pixels: int
    feathered_pixels: int
    colour_adjusted_pixels: int
    gap_repairs: int


class TextureRefinementService:
    """Refine a triangulated reconstruction without changing untouched donor UV areas."""

    def refine(self, reconstruction_manifest: Path, settings: RefinementSettings = RefinementSettings()) -> RefinementResult:
        payload = self._json(reconstruction_manifest)
        if payload.get("format") != "facestudio-texture-reconstruction-v1":
            raise ValueError("Expected a facestudio-texture-reconstruction-v1 manifest.")
        player_id = str(payload.get("player_id", ""))
        if not player_id.isdigit():
            raise ValueError("Reconstruction manifest has an invalid player ID.")
        donor_path = Path(str(payload.get("donor_texture", ""))).expanduser()
        raw_path = Path(str(payload.get("output_texture", ""))).expanduser()
        donor = self._read(donor_path).convertToFormat(QImage.Format.Format_ARGB32)
        raw = self._read(raw_path).convertToFormat(QImage.Format.Format_ARGB32)
        if donor.size() != raw.size():
            raise ValueError("Donor and reconstructed textures must have identical dimensions.")

        settings = settings.normalised()
        mask = self._changed_mask(donor, raw)
        changed = sum(mask)
        if changed == 0:
            raise ValueError("The reconstruction contains no changed facial pixels to refine.")

        repaired, repairs = self._repair_gaps(mask, raw.width(), raw.height())
        colourised, colour_count = self._colour_match(donor, raw, repaired, settings.colour_matching)
        smoothed = self._neighbour_smooth(colourised, repaired, settings.neighbour_blend)
        output, feathered = self._feather(donor, smoothed, repaired, settings.feather_radius)
        return RefinementResult(
            player_id, str(donor_path), str(raw_path), output, settings,
            changed, feathered, colour_count, repairs,
        )

    @staticmethod
    def save(result: RefinementResult, destination: Path) -> tuple[Path, Path]:
        png = destination.with_suffix(".png")
        if not result.output.save(str(png), "PNG"):
            raise OSError(f"Could not save refined texture: {png}")
        manifest = png.with_suffix(".json")
        manifest.write_text(json.dumps({
            "format": REFINEMENT_FORMAT,
            "player_id": result.player_id,
            "donor_texture": result.donor_texture,
            "raw_texture": result.raw_texture,
            "output_texture": str(png),
            "settings": {
                "feather_radius": result.settings.feather_radius,
                "colour_matching": result.settings.colour_matching,
                "neighbour_blend": result.settings.neighbour_blend,
            },
            "changed_pixels": result.changed_pixels,
            "feathered_pixels": result.feathered_pixels,
            "colour_adjusted_pixels": result.colour_adjusted_pixels,
            "gap_repairs": result.gap_repairs,
            "next_stage": "fm-texture-validation-and-controlled-game-test",
        }, indent=2), encoding="utf-8")
        return png, manifest

    @staticmethod
    def _changed_mask(donor: QImage, raw: QImage) -> list[bool]:
        mask: list[bool] = []
        for y in range(raw.height()):
            for x in range(raw.width()):
                a, b = donor.pixelColor(x, y), raw.pixelColor(x, y)
                mask.append(abs(a.red()-b.red()) + abs(a.green()-b.green()) + abs(a.blue()-b.blue()) > 4)
        return mask

    @staticmethod
    def _repair_gaps(mask: list[bool], width: int, height: int) -> tuple[list[bool], int]:
        repaired = mask.copy(); count = 0
        for y in range(1, height-1):
            for x in range(1, width-1):
                i = y*width+x
                if repaired[i]:
                    continue
                neighbours = sum(mask[(y+dy)*width+(x+dx)] for dx,dy in ((-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,-1),(-1,1),(1,1)))
                if neighbours >= 6:
                    repaired[i] = True; count += 1
        return repaired, count

    @staticmethod
    def _colour_match(donor: QImage, raw: QImage, mask: list[bool], strength: float) -> tuple[QImage, int]:
        output = raw.copy()
        if strength <= 0:
            return output, 0
        donor_sum = [0.0,0.0,0.0]; raw_sum = [0.0,0.0,0.0]; count = 0
        for y in range(raw.height()):
            for x in range(raw.width()):
                if not mask[y*raw.width()+x]: continue
                d, r = donor.pixelColor(x,y), raw.pixelColor(x,y)
                for k,v in enumerate((d.red(),d.green(),d.blue())): donor_sum[k]+=v
                for k,v in enumerate((r.red(),r.green(),r.blue())): raw_sum[k]+=v
                count += 1
        if not count: return output, 0
        offsets = [(donor_sum[k]-raw_sum[k])/count*strength for k in range(3)]
        for y in range(raw.height()):
            for x in range(raw.width()):
                if not mask[y*raw.width()+x]: continue
                c=raw.pixelColor(x,y)
                values=[max(0,min(255,round(v+offsets[k]))) for k,v in enumerate((c.red(),c.green(),c.blue()))]
                output.setPixelColor(x,y,QColor(*values,255))
        return output, count

    @staticmethod
    def _neighbour_smooth(image: QImage, mask: list[bool], strength: float) -> QImage:
        if strength <= 0: return image.copy()
        output=image.copy(); w=image.width(); h=image.height()
        for y in range(1,h-1):
            for x in range(1,w-1):
                if not mask[y*w+x]: continue
                colours=[image.pixelColor(x+dx,y+dy) for dx,dy in ((0,0),(-1,0),(1,0),(0,-1),(0,1)) if mask[(y+dy)*w+(x+dx)]]
                if len(colours)<2: continue
                base=image.pixelColor(x,y)
                avg=[sum(getattr(c,n)() for c in colours)/len(colours) for n in ("red","green","blue")]
                vals=[round(v*(1-strength)+avg[k]*strength) for k,v in enumerate((base.red(),base.green(),base.blue()))]
                output.setPixelColor(x,y,QColor(*vals,255))
        return output

    @staticmethod
    def _feather(donor: QImage, refined: QImage, mask: list[bool], radius: int) -> tuple[QImage,int]:
        if radius <= 0: return refined.copy(), 0
        output=donor.copy(); w=refined.width(); h=refined.height(); feathered=0
        inside=[10_000 if m else 0 for m in mask]
        for _ in range(radius):
            nxt=inside.copy()
            for y in range(1,h-1):
                for x in range(1,w-1):
                    i=y*w+x
                    if not mask[i]: continue
                    nxt[i]=min(inside[i],1+min(inside[i-1],inside[i+1],inside[i-w],inside[i+w]))
            inside=nxt
        for y in range(h):
            for x in range(w):
                i=y*w+x
                if not mask[i]: continue
                alpha=min(1.0, inside[i]/max(1,radius))
                if alpha < 1.0: feathered += 1
                a=donor.pixelColor(x,y); b=refined.pixelColor(x,y)
                output.setPixelColor(x,y,QColor(round(a.red()*(1-alpha)+b.red()*alpha),round(a.green()*(1-alpha)+b.green()*alpha),round(a.blue()*(1-alpha)+b.blue()*alpha),255))
        return output, feathered

    @staticmethod
    def _json(path: Path) -> dict:
        try: return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc: raise ValueError(f"Could not read reconstruction manifest: {exc}") from exc

    @staticmethod
    def _read(path: Path) -> QImage:
        reader=QImageReader(str(path)); reader.setAutoTransform(True); image=reader.read()
        if image.isNull(): raise ValueError(f"Texture could not be decoded: {path}")
        return image
