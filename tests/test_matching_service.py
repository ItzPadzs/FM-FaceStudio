import json
from pathlib import Path

from facestudio.matching.service import MatchingService


def test_matching_service_writes_results(tmp_path: Path) -> None:
    analysis = {
        "face_shape": "round",
        "measurements": {
            "face_height_width_ratio": 1.02,
            "inter_eye_face_width_ratio": 0.36,
            "eye_line_face_height_ratio": 0.40,
            "mouth_line_face_height_ratio": 0.76,
        },
    }
    candidates = [
        {
            "candidate_id": "round",
            "display_name": "Round",
            "descriptor": {
                "face_height_width_ratio": 1.03,
                "inter_eye_face_width_ratio": 0.36,
                "eye_line_face_height_ratio": 0.40,
                "mouth_line_face_height_ratio": 0.76,
                "face_shape": "round",
            },
        },
        {
            "candidate_id": "oblong",
            "display_name": "Oblong",
            "descriptor": {
                "face_height_width_ratio": 1.50,
                "inter_eye_face_width_ratio": 0.30,
                "eye_line_face_height_ratio": 0.36,
                "mouth_line_face_height_ratio": 0.80,
                "face_shape": "oblong",
            },
        },
    ]

    analysis_path = tmp_path / "analysis.json"
    catalogue_path = tmp_path / "catalogue.json"
    output_path = tmp_path / "matches.json"
    analysis_path.write_text(json.dumps(analysis), encoding="utf-8")
    catalogue_path.write_text(json.dumps(candidates), encoding="utf-8")

    results = MatchingService().match_project(
        analysis_path,
        catalogue_path,
        output_path,
    )

    assert results[0].candidate.candidate_id == "round"
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["results"][0]["rank"] == 1
