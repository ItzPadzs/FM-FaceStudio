from facestudio.matching.engine import FaceMatcher
from facestudio.matching.models import FaceDescriptor, MatchCandidate


def descriptor(
    face_ratio: float,
    eye_ratio: float = 0.35,
    eye_line: float = 0.40,
    mouth_line: float = 0.76,
    shape: str = "oval",
) -> FaceDescriptor:
    return FaceDescriptor(
        face_height_width_ratio=face_ratio,
        inter_eye_face_width_ratio=eye_ratio,
        eye_line_face_height_ratio=eye_line,
        mouth_line_face_height_ratio=mouth_line,
        face_shape=shape,
    )


def test_identical_descriptor_scores_one() -> None:
    target = descriptor(1.30)
    candidate = MatchCandidate("one", "One", target)
    result = FaceMatcher().compare(target, candidate)
    assert result.similarity == 1.0


def test_closest_candidate_ranks_first() -> None:
    target = descriptor(1.30)
    close = MatchCandidate("close", "Close", descriptor(1.31))
    far = MatchCandidate("far", "Far", descriptor(1.80, shape="round"))
    results = FaceMatcher().rank(target, [far, close])
    assert results[0].candidate.candidate_id == "close"
    assert results[0].similarity > results[1].similarity


def test_shape_compatibility_is_partial() -> None:
    matcher = FaceMatcher()
    target = descriptor(1.30, shape="oval")
    exact = MatchCandidate("exact", "Exact", descriptor(1.30, shape="oval"))
    compatible = MatchCandidate(
        "compatible",
        "Compatible",
        descriptor(1.30, shape="oblong"),
    )
    assert matcher.compare(target, exact).similarity > matcher.compare(
        target, compatible
    ).similarity
