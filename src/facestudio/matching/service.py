from __future__ import annotations

import json
from pathlib import Path

from facestudio.matching.catalogue import CandidateCatalogue
from facestudio.matching.engine import FaceMatcher
from facestudio.matching.models import FaceDescriptor, MatchResult


class MatchingService:
    def __init__(self) -> None:
        self.matcher = FaceMatcher()
        self.catalogue = CandidateCatalogue()

    def match_project(
        self,
        analysis_path: Path,
        catalogue_path: Path,
        output_path: Path,
        limit: int = 10,
    ) -> list[MatchResult]:
        analysis_payload = json.loads(
            analysis_path.read_text(encoding="utf-8")
        )
        target = FaceDescriptor.from_analysis_payload(analysis_payload)
        candidates = self.catalogue.load(catalogue_path)
        results = self.matcher.rank(target, candidates, limit=limit)

        payload = {
            "schema_version": 1,
            "analysis_file": analysis_path.name,
            "catalogue_file": catalogue_path.name,
            "results": [
                {
                    "rank": rank,
                    "candidate_id": result.candidate.candidate_id,
                    "display_name": result.candidate.display_name,
                    "similarity": round(result.similarity, 6),
                    "distance": round(result.distance, 6),
                    "source": result.candidate.source,
                    "notes": result.candidate.notes,
                    "component_scores": {
                        name: round(score, 6)
                        for name, score in result.component_scores.items()
                    },
                }
                for rank, result in enumerate(results, start=1)
            ],
        }

        temporary = output_path.with_suffix(output_path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(output_path)
        return results
