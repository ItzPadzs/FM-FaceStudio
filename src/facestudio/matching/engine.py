from __future__ import annotations

import math
from collections.abc import Iterable

from facestudio.matching.models import (
    FaceDescriptor,
    MatchCandidate,
    MatchResult,
)


DEFAULT_WEIGHTS = {
    "face_height_width_ratio": 0.34,
    "inter_eye_face_width_ratio": 0.28,
    "eye_line_face_height_ratio": 0.16,
    "mouth_line_face_height_ratio": 0.14,
    "face_shape": 0.08,
}

DEFAULT_SCALES = {
    "face_height_width_ratio": 0.35,
    "inter_eye_face_width_ratio": 0.15,
    "eye_line_face_height_ratio": 0.18,
    "mouth_line_face_height_ratio": 0.18,
}


class FaceMatcher:
    def __init__(
        self,
        weights: dict[str, float] | None = None,
        scales: dict[str, float] | None = None,
    ) -> None:
        self.weights = dict(DEFAULT_WEIGHTS if weights is None else weights)
        self.scales = dict(DEFAULT_SCALES if scales is None else scales)

    @staticmethod
    def _numeric_component(
        left: float,
        right: float,
        scale: float,
    ) -> tuple[float, float]:
        delta = abs(left - right)
        normalised = delta / max(scale, 1e-9)
        score = math.exp(-(normalised ** 2))
        return score, normalised

    @staticmethod
    def _shape_score(left: str, right: str) -> float:
        left = left.strip().lower()
        right = right.strip().lower()
        if left == right:
            return 1.0

        compatible = {
            frozenset({"round", "square / round"}),
            frozenset({"oval", "oblong"}),
            frozenset({"oval", "square / round"}),
        }
        return 0.62 if frozenset({left, right}) in compatible else 0.20

    def compare(
        self,
        target: FaceDescriptor,
        candidate: MatchCandidate,
    ) -> MatchResult:
        components: dict[str, float] = {}
        distances: list[tuple[float, float]] = []

        for name in (
            "face_height_width_ratio",
            "inter_eye_face_width_ratio",
            "eye_line_face_height_ratio",
            "mouth_line_face_height_ratio",
        ):
            score, distance = self._numeric_component(
                float(getattr(target, name)),
                float(getattr(candidate.descriptor, name)),
                self.scales[name],
            )
            components[name] = score
            distances.append((distance, self.weights[name]))

        shape_score = self._shape_score(
            target.face_shape,
            candidate.descriptor.face_shape,
        )
        components["face_shape"] = shape_score
        distances.append((1.0 - shape_score, self.weights["face_shape"]))

        total_weight = sum(self.weights.values())
        similarity = sum(
            components[name] * self.weights[name]
            for name in self.weights
        ) / total_weight
        weighted_distance = sum(
            distance * weight for distance, weight in distances
        ) / total_weight

        return MatchResult(
            candidate=candidate,
            similarity=max(0.0, min(1.0, similarity)),
            distance=weighted_distance,
            component_scores=components,
        )

    def rank(
        self,
        target: FaceDescriptor,
        candidates: Iterable[MatchCandidate],
        limit: int = 10,
    ) -> list[MatchResult]:
        results = [
            self.compare(target, candidate)
            for candidate in candidates
        ]
        results.sort(
            key=lambda result: (
                -result.similarity,
                result.candidate.display_name.lower(),
            )
        )
        return results[: max(1, limit)]
