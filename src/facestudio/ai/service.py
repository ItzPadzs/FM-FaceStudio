from __future__ import annotations

import json
from pathlib import Path

import cv2

from facestudio.ai.analyzer import FaceAnalysisError, FaceAnalyzer
from facestudio.ai.models import FaceAnalysis


class FaceAnalysisService:
    def __init__(self) -> None:
        self.analyzer = FaceAnalyzer()

    def analyze_project_photo(
        self,
        source_path: Path,
        project_directory: Path,
    ) -> tuple[FaceAnalysis, Path, Path]:
        analysis, overlay = self.analyzer.analyze(source_path)

        analysis_path = project_directory / "analysis.json"
        preview_path = project_directory / "preview.png"

        temporary = analysis_path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(analysis.to_dict(), indent=2),
            encoding="utf-8",
        )
        temporary.replace(analysis_path)

        if not cv2.imwrite(str(preview_path), overlay):
            raise FaceAnalysisError("The analysis preview could not be written.")

        return analysis, analysis_path, preview_path
