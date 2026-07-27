from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from PySide6.QtGui import QColor, QImage, QImageReader

from facestudio.match_engine_research.one_click_face_builder import LANDMARK_ORDER, Landmark

RECONSTRUCTION_FORMAT = "facestudio-texture-reconstruction-v1"
TRIANGLES = (
    ("face_top", "left_temple", "nose_bridge"),
    ("face_top", "nose_bridge", "right_temple"),
    ("left_temple", "left_eye", "nose_bridge"),
    ("right_temple", "nose_bridge", "right_eye"),
    ("left_eye", "nose_bridge", "nose_tip"),
    ("right_eye", "nose_tip", "nose_bridge"),
    ("left_temple", "left_jaw", "left_eye"),
    ("right_temple", "right_eye", "right_jaw"),
    ("left_eye", "left_jaw", "left_mouth"),
    ("right_eye", "right_mouth", "right_jaw"),
    ("left_eye", "left_mouth", "nose_tip"),
    ("right_eye", "nose_tip", "right_mouth"),
    ("left_mouth", "left_jaw", "chin"),
    ("right_mouth", "chin", "right_jaw"),
    ("left_mouth", "chin", "right_mouth"),
)

@dataclass(frozen=True)
class ReconstructionResult:
    player_id: str
    donor_texture: str
    output: QImage
    triangles_written: int
    pixels_written: int
    skipped_hair_pixels: int

class TextureReconstructionService:
    """Warp a reviewed portrait into reviewed donor UV anchors triangle by triangle."""

    def load_portrait_record(self, path: Path) -> tuple[Path, tuple[Landmark, ...]]:
        payload = self._json(path)
        if payload.get("format") != "facestudio-landmarks-v1":
            raise ValueError("Expected a facestudio-landmarks-v1 portrait record.")
        source = Path(str(payload.get("source_path", ""))).expanduser()
        if not source.is_file():
            raise ValueError(f"Portrait image not found: {source}")
        return source, self._landmarks(payload.get("landmarks"), "portrait")

    def load_uv_record(self, path: Path) -> tuple[str, Path, tuple[Landmark, ...]]:
        payload = self._json(path)
        if payload.get("format") != "facestudio-donor-uv-calibration-v1":
            raise ValueError("Expected a facestudio-donor-uv-calibration-v1 record.")
        if not payload.get("complete"):
            raise ValueError("UV calibration is incomplete; review all anchors first.")
        player_id = str(payload.get("player_id", ""))
        if not player_id.isdigit():
            raise ValueError("UV calibration has an invalid donor player ID.")
        texture = Path(str(payload.get("texture_path", ""))).expanduser()
        if not texture.is_file():
            raise ValueError(f"Donor texture not found: {texture}")
        return player_id, texture, self._landmarks(payload.get("anchors"), "UV")

    def reconstruct(self, portrait_record: Path, uv_record: Path, opacity: float = 0.92) -> ReconstructionResult:
        opacity = max(0.0, min(1.0, float(opacity)))
        portrait_path, source_points = self.load_portrait_record(portrait_record)
        player_id, donor_path, destination_points = self.load_uv_record(uv_record)
        source = self._read(portrait_path).convertToFormat(QImage.Format.Format_ARGB32)
        donor = self._read(donor_path).convertToFormat(QImage.Format.Format_ARGB32)
        output = donor.copy()
        src = {p.name: (p.x * (source.width()-1), p.y * (source.height()-1)) for p in source_points}
        dst = {p.name: (p.x * (donor.width()-1), p.y * (donor.height()-1)) for p in destination_points}
        written = skipped = triangles = 0
        for names in TRIANGLES:
            count, ignored = self._warp_triangle(source, output, tuple(src[n] for n in names), tuple(dst[n] for n in names), opacity)
            if count:
                triangles += 1
            written += count; skipped += ignored
        return ReconstructionResult(player_id, str(donor_path), output, triangles, written, skipped)

    @staticmethod
    def save(result: ReconstructionResult, destination: Path) -> tuple[Path, Path]:
        png = destination.with_suffix(".png")
        if not result.output.save(str(png), "PNG"):
            raise OSError(f"Could not save reconstructed texture: {png}")
        manifest = png.with_suffix(".json")
        manifest.write_text(json.dumps({
            "format": RECONSTRUCTION_FORMAT,
            "player_id": result.player_id,
            "donor_texture": result.donor_texture,
            "output_texture": str(png),
            "triangles_written": result.triangles_written,
            "pixels_written": result.pixels_written,
            "skipped_hair_pixels": result.skipped_hair_pixels,
            "hair_and_facial_hair": "excluded-by-dark-pixel-guard",
            "next_stage": "seam-blending-and-game-preview",
        }, indent=2), encoding="utf-8")
        return png, manifest

    def _warp_triangle(self, source: QImage, output: QImage, s, d, opacity: float) -> tuple[int, int]:
        min_x=max(0,int(min(p[0] for p in d))); max_x=min(output.width()-1,int(max(p[0] for p in d))+1)
        min_y=max(0,int(min(p[1] for p in d))); max_y=min(output.height()-1,int(max(p[1] for p in d))+1)
        den=(d[1][1]-d[2][1])*(d[0][0]-d[2][0])+(d[2][0]-d[1][0])*(d[0][1]-d[2][1])
        if abs(den)<1e-8: return 0,0
        written=skipped=0
        for y in range(min_y,max_y+1):
            for x in range(min_x,max_x+1):
                a=((d[1][1]-d[2][1])*(x-d[2][0])+(d[2][0]-d[1][0])*(y-d[2][1]))/den
                b=((d[2][1]-d[0][1])*(x-d[2][0])+(d[0][0]-d[2][0])*(y-d[2][1]))/den
                c=1-a-b
                if a < -0.002 or b < -0.002 or c < -0.002: continue
                sx=int(round(a*s[0][0]+b*s[1][0]+c*s[2][0])); sy=int(round(a*s[0][1]+b*s[1][1]+c*s[2][1]))
                sx=max(0,min(source.width()-1,sx)); sy=max(0,min(source.height()-1,sy))
                colour=source.pixelColor(sx,sy)
                if self._hair_like(colour): skipped+=1; continue
                base=output.pixelColor(x,y)
                output.setPixelColor(x,y,QColor(round(base.red()*(1-opacity)+colour.red()*opacity),round(base.green()*(1-opacity)+colour.green()*opacity),round(base.blue()*(1-opacity)+colour.blue()*opacity),255))
                written+=1
        return written, skipped

    @staticmethod
    def _hair_like(colour: QColor) -> bool:
        maximum=max(colour.red(),colour.green(),colour.blue()); minimum=min(colour.red(),colour.green(),colour.blue())
        return maximum < 72 and (maximum-minimum) < 38

    @staticmethod
    def _json(path: Path) -> dict:
        try: return json.loads(path.read_text(encoding="utf-8"))
        except (OSError,json.JSONDecodeError) as exc: raise ValueError(f"Could not read JSON record: {exc}") from exc

    @staticmethod
    def _landmarks(raw, label: str) -> tuple[Landmark,...]:
        if not isinstance(raw,list): raise ValueError(f"{label} record is missing landmarks.")
        values={str(item.get("name")): item for item in raw if isinstance(item,dict)}
        if set(values) != set(LANDMARK_ORDER): raise ValueError(f"{label} record must contain all twelve named landmarks.")
        return tuple(Landmark(name,float(values[name]["x"]),float(values[name]["y"]),float(values[name].get("confidence",1.0))) for name in LANDMARK_ORDER)

    @staticmethod
    def _read(path: Path) -> QImage:
        reader=QImageReader(str(path)); reader.setAutoTransform(True); image=reader.read()
        if image.isNull(): raise ValueError(f"Image could not be decoded: {path}")
        return image
