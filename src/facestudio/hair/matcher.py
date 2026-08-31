from __future__ import annotations

from collections.abc import Iterable, Sequence
import math

from facestudio.hair.models import HairCandidate, HairDescriptor, HairMatchResult


DEFAULT_WEIGHTS = {
    "front_silhouette": 0.30,
    "side_silhouette": 0.24,
    "top_silhouette": 0.12,
    "width_height": 0.11,
    "depth_height": 0.09,
    "width_depth": 0.05,
    "vertical_mass": 0.04,
    "structure": 0.05,
}


class HairMatcher:
    """Rank native FM donor hair by visual shape, not raw topology identity.

    Structural counts are intentionally a small secondary term because the corpus
    contains several legitimate FM hair families.  UV range, winding direction,
    alpha type and normal-map filename are *not* normalised or treated as defects.
    """

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self.weights = dict(DEFAULT_WEIGHTS if weights is None else weights)

    @staticmethod
    def _jaccard(left: Sequence[int], right: Sequence[int]) -> float:
        size = min(len(left), len(right))
        if size == 0:
            return 0.0
        intersection = 0
        union = 0
        for index in range(size):
            a = bool(left[index])
            b = bool(right[index])
            intersection += int(a and b)
            union += int(a or b)
        return intersection / union if union else 1.0

    @staticmethod
    def _ratio_score(left: float, right: float, log_scale: float = 0.35) -> float:
        if left <= 0 or right <= 0:
            return 0.0
        delta = abs(math.log(left / right))
        return math.exp(-((delta / max(log_scale, 1e-9)) ** 2))

    @staticmethod
    def _linear_score(left: float, right: float, scale: float = 0.30) -> float:
        return math.exp(-((abs(left - right) / max(scale, 1e-9)) ** 2))

    @staticmethod
    def _structure_score(target: HairDescriptor, candidate: HairDescriptor) -> float:
        if target.component_count <= 0 or candidate.component_count <= 0:
            return 0.5
        component = HairMatcher._ratio_score(
            max(1.0, float(target.component_count)),
            max(1.0, float(candidate.component_count)),
            log_scale=1.15,
        )
        vertices = HairMatcher._ratio_score(
            max(1.0, float(target.vertex_count)),
            max(1.0, float(candidate.vertex_count)),
            log_scale=1.75,
        )
        triangles = HairMatcher._ratio_score(
            max(1.0, float(target.triangle_count)),
            max(1.0, float(candidate.triangle_count)),
            log_scale=1.75,
        )
        return 0.50 * component + 0.25 * vertices + 0.25 * triangles

    def compare(self, target: HairDescriptor, candidate: HairCandidate) -> HairMatchResult:
        descriptor = candidate.descriptor
        components = {
            "front_silhouette": self._jaccard(target.front_occupancy, descriptor.front_occupancy),
            "side_silhouette": self._jaccard(target.side_occupancy, descriptor.side_occupancy),
            "top_silhouette": self._jaccard(target.top_occupancy, descriptor.top_occupancy),
            "width_height": self._ratio_score(target.width_height_ratio, descriptor.width_height_ratio),
            "depth_height": self._ratio_score(target.depth_height_ratio, descriptor.depth_height_ratio),
            "width_depth": self._ratio_score(target.width_depth_ratio, descriptor.width_depth_ratio),
            "vertical_mass": self._linear_score(target.centroid_y_ratio, descriptor.centroid_y_ratio, 0.22),
            "structure": self._structure_score(target, descriptor),
        }
        total_weight = sum(self.weights.values()) or 1.0
        base = sum(components[name] * self.weights[name] for name in self.weights) / total_weight

        warnings: list[str] = []
        score = base
        if candidate.proven:
            # A proven in-game set is more trustworthy, but visual mismatch must still win.
            score += 0.025 * (1.0 - score)
        if not candidate.contract.complete:
            score *= 0.70
            warnings.append("incomplete native hair contract")
        if not candidate.contract.normal_files:
            warnings.append("donor supplies no normal map")

        return HairMatchResult(
            candidate=candidate,
            similarity=max(0.0, min(1.0, score)),
            base_similarity=max(0.0, min(1.0, base)),
            component_scores=components,
            warnings=tuple(warnings),
        )

    def rank(
        self,
        target: HairDescriptor,
        candidates: Iterable[HairCandidate],
        limit: int | None = 25,
    ) -> list[HairMatchResult]:
        results = [self.compare(target, candidate) for candidate in candidates]
        results.sort(
            key=lambda result: (
                -result.similarity,
                not result.candidate.proven,
                result.candidate.display_name.lower(),
                result.candidate.candidate_id,
            )
        )
        if limit is None:
            return results
        return results[: max(1, int(limit))]
