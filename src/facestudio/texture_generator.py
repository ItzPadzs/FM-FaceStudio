from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps

UV_TEXTURE_FORMAT = "facestudio-head-texture-v1"


@dataclass(frozen=True)
class TextureBuildResult:
    texture: Path
    manifest: Path
    size: int


class HeadTextureGenerator:
    """Generate an editable 1024-square head texture from one frontal portrait.

    The target layout is derived from the supplied FM/BepInEx examples: forehead at
    y 0.15-0.32, eyes near y 0.38, nose near y 0.50, mouth near y 0.61, chin near
    y 0.75, ears near x 0.13/0.87, and stretched neck/side coverage below y 0.72.
    """

    def build(
        self,
        photo: Path,
        output_directory: Path,
        *,
        template: Path | None = None,
        size: int = 1024,
        face_scale: float = 1.0,
        face_y: float = 0.0,
        smoothing: float = 0.35,
    ) -> TextureBuildResult:
        photo = Path(photo).expanduser().resolve()
        output_directory = Path(output_directory).expanduser().resolve()
        if not photo.is_file():
            raise ValueError(f"Photograph not found: {photo}")
        if size not in (512, 1024, 2048):
            raise ValueError("Texture size must be 512, 1024 or 2048")
        output_directory.mkdir(parents=True, exist_ok=True)

        source = Image.open(photo).convert("RGB")
        source = ImageOps.exif_transpose(source)
        source = self._square_face_crop(source, face_scale, face_y)
        source = source.resize((size, size), Image.Resampling.LANCZOS)

        if template:
            template_path = Path(template).expanduser().resolve()
            if not template_path.is_file():
                raise ValueError(f"Template not found: {template_path}")
            canvas = Image.open(template_path).convert("RGB").resize((size, size), Image.Resampling.LANCZOS)
        else:
            canvas = self._neutral_canvas(source, size)

        face = self._warp_central_face(source, size)
        mask = self._face_mask(size).filter(ImageFilter.GaussianBlur(max(2, int(size * 0.018))))
        canvas.paste(face, (0, 0), mask)
        canvas = self._extend_sides(canvas, size)
        canvas = self._extend_neck(canvas, size)
        canvas = self._soften_seams(canvas, smoothing)

        texture = output_directory / f"{photo.stem}-head-texture.png"
        canvas.save(texture, "PNG")
        manifest = output_directory / f"{photo.stem}-head-texture.json"
        manifest.write_text(json.dumps({
            "format": UV_TEXTURE_FORMAT,
            "source_photo": str(photo),
            "template": str(template) if template else None,
            "texture": str(texture),
            "size": size,
            "face_scale": face_scale,
            "face_y": face_y,
            "smoothing": smoothing,
            "target_layout": {
                "left_ear": [0.13, 0.48], "right_ear": [0.87, 0.48],
                "left_eye": [0.39, 0.39], "right_eye": [0.61, 0.39],
                "nose": [0.50, 0.51], "mouth": [0.50, 0.62],
                "chin": [0.50, 0.75], "hair_split": [0.50, 0.02],
                "neck_start": 0.73,
            },
            "boundary": "Produces a 2D UV-style texture only; it does not create or alter mesh geometry.",
        }, indent=2), encoding="utf-8")
        return TextureBuildResult(texture, manifest, size)

    @staticmethod
    def _square_face_crop(image: Image.Image, scale: float, y_offset: float) -> Image.Image:
        width, height = image.size
        side = int(min(width, height) / max(0.65, min(1.6, scale)))
        cx = width // 2
        cy = int(height * (0.50 + max(-0.25, min(0.25, y_offset))))
        left = max(0, min(width - side, cx - side // 2))
        top = max(0, min(height - side, cy - side // 2))
        return image.crop((left, top, left + side, top + side))

    @staticmethod
    def _neutral_canvas(source: Image.Image, size: int) -> Image.Image:
        sample = source.crop((int(size * .36), int(size * .58), int(size * .64), int(size * .82)))
        colour = tuple(int(v) for v in ImageStatMean.mean(sample))
        return Image.new("RGB", (size, size), colour)

    @staticmethod
    def _warp_central_face(source: Image.Image, size: int) -> Image.Image:
        # Preserve the observed central feature spacing while widening the jaw and neck.
        resized = source.resize((int(size * .70), int(size * .82)), Image.Resampling.LANCZOS)
        out = Image.new("RGB", (size, size), resized.getpixel((resized.width // 2, resized.height - 1)))
        out.paste(resized, (int(size * .15), int(size * .10)))
        return out

    @staticmethod
    def _face_mask(size: int) -> Image.Image:
        mask = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((int(size*.14), int(size*.07), int(size*.86), int(size*.92)), fill=255)
        draw.rectangle((int(size*.20), int(size*.50), int(size*.80), int(size*.90)), fill=255)
        return mask

    @staticmethod
    def _extend_sides(image: Image.Image, size: int) -> Image.Image:
        out = image.copy()
        left = image.crop((int(size*.15), int(size*.18), int(size*.31), int(size*.92))).resize((int(size*.22), int(size*.74)), Image.Resampling.BICUBIC)
        right = ImageOps.mirror(image.crop((int(size*.69), int(size*.18), int(size*.85), int(size*.92)))).resize((int(size*.22), int(size*.74)), Image.Resampling.BICUBIC)
        out.paste(left, (0, int(size*.18)))
        out.paste(ImageOps.mirror(right), (int(size*.78), int(size*.18)))
        return out

    @staticmethod
    def _extend_neck(image: Image.Image, size: int) -> Image.Image:
        out = image.copy()
        strip = image.crop((int(size*.20), int(size*.70), int(size*.80), int(size*.86)))
        strip = strip.resize((size, int(size*.30)), Image.Resampling.BICUBIC)
        out.paste(strip, (0, int(size*.70)))
        return out

    @staticmethod
    def _soften_seams(image: Image.Image, amount: float) -> Image.Image:
        amount = max(0.0, min(1.0, amount))
        blurred = image.filter(ImageFilter.GaussianBlur(max(0.1, image.width * 0.004)))
        return Image.blend(image, blurred, amount * 0.25)


class ImageStatMean:
    @staticmethod
    def mean(image: Image.Image) -> tuple[float, float, float]:
        tiny = image.resize((1, 1), Image.Resampling.BOX)
        return tiny.getpixel((0, 0))
