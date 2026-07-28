from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QImageReader

from facestudio.ai.generation_engine import GenerationRequest, GenerationResult, ProgressCallback


class TrainedPortraitUVEngine:
    name = "trained-portrait-uv-v1"

    def __init__(self, model_dir: Path) -> None:
        self.model_dir = Path(model_dir)
        self.manifest_path = self.model_dir / "model-manifest.json"

    @property
    def available(self) -> bool:
        if not self.manifest_path.is_file():
            return False
        try:
            manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            return (self.model_dir / manifest["checkpoint"]).is_file()
        except Exception:
            return False

    @property
    def status_message(self) -> str:
        return "Trained portrait-to-UV model is ready." if self.available else "No trained portrait-to-UV weights installed."

    def generate(self, request: GenerationRequest, progress: ProgressCallback | None = None) -> GenerationResult:
        if not self.available:
            raise RuntimeError("No trained FaceStudio model is installed. Train or install model-manifest.json and its checkpoint first.")
        try:
            import torch
            from torchvision import transforms
            from PIL import Image
        except ImportError as exc:
            raise RuntimeError("Install the model extra: python -m pip install -e .[training]") from exc
        from facestudio.training.portrait_uv import build_generator

        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        checkpoint = torch.load(self.model_dir / manifest["checkpoint"], map_location="cpu")
        size = int(manifest.get("image_size", checkpoint.get("image_size", 512)))
        model = build_generator()
        model.load_state_dict(checkpoint["model"])
        model.eval()
        if progress: progress(15, "Loading trained portrait-to-UV model", None)

        portrait = Image.open(request.portrait).convert("RGB")
        transform = transforms.Compose([
            transforms.Resize((size, size)), transforms.ToTensor(), transforms.Normalize((.5,)*3, (.5,)*3)
        ])
        tensor = transform(portrait).unsqueeze(0)
        if progress: progress(35, "Encoding portrait identity", None)
        with torch.inference_mode():
            prediction = model(tensor)[0].clamp(-1,1).add(1).div(2)
        if progress: progress(75, "Generating canonical FM UV texture", None)
        array = prediction.mul(255).byte().permute(1,2,0).cpu().numpy()
        generated = Image.fromarray(array, mode="RGB").resize((1024,1024), Image.Resampling.LANCZOS)
        output = Path(request.output).expanduser().resolve(); output.parent.mkdir(parents=True, exist_ok=True)
        generated.save(output, "PNG")
        if progress: progress(100, "Trained portrait-to-UV generation complete", output)
        return GenerationResult(
            output=output, engine=self.name, donor_id=request.donor_id, donor_name=request.donor_name,
            stages=("Model load","Identity encoding","Portrait-to-UV inference","1024x1024 export"),
            metadata={"trained_model":True,"model_format":manifest.get("format"),"training_pairs":manifest.get("pairs"),"output_size":[1024,1024]},
        )
