from facestudio.ai.models import FaceAnalysis, Point, Rect


def test_analysis_serialisation() -> None:
    analysis = FaceAnalysis(
        image_width=100,
        image_height=200,
        face_box=Rect(10, 20, 40, 80),
        landmarks={
            "left_eye": Point(0.3, 0.4, "detected", 0.8),
        },
        measurements={"face_height_width_ratio": 2.0},
        face_shape="oblong",
        confidence=0.75,
    )
    payload = analysis.to_dict()
    assert payload["schema_version"] == 1
    assert payload["face_box"]["width"] == 40
    assert payload["landmarks"]["left_eye"]["source"] == "detected"
