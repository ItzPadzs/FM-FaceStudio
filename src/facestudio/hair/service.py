from __future__ import annotations

import json
from pathlib import Path

from facestudio.hair.library import HairLibrary
from facestudio.hair.matcher import HairMatcher
from facestudio.hair.models import HairDescriptor, HairMatchResult, HairSelection
from facestudio.hair.skin import describe_hair_skin


class HairMatchingService:
    def __init__(
        self,
        cache_path: Path | None = None,
        proven_path: Path | None = None,
    ) -> None:
        self.library = HairLibrary(cache_path=cache_path, proven_path=proven_path)
        self.matcher = HairMatcher()

    def rank_skin_against_library(
        self,
        source_hair_skin: str | Path,
        library_root: str | Path,
        limit: int | None = 50,
    ) -> list[HairMatchResult]:
        target = describe_hair_skin(source_hair_skin)
        return self.rank_descriptor_against_library(target, library_root, limit=limit)

    def rank_descriptor_against_library(
        self,
        target: HairDescriptor,
        library_root: str | Path,
        limit: int | None = 50,
    ) -> list[HairMatchResult]:
        candidates = self.library.scan(library_root)
        return self.matcher.rank(target, candidates, limit=limit)

    @staticmethod
    def write_report(
        output_path: str | Path,
        results: list[HairMatchResult],
        *,
        source: str,
        library_root: str,
    ) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "source": source,
            "library_root": library_root,
            "policy": {
                "native_asset_contract_preserved": True,
                "uvs_normalised": False,
                "alpha_normalised": False,
                "normal_aliases_created": False,
                "winding_normalised": False,
            },
            "results": [
                {
                    "rank": index,
                    "candidate_id": result.candidate.candidate_id,
                    "uid": result.candidate.contract.uid,
                    "display_name": result.candidate.display_name,
                    "similarity": round(result.similarity, 6),
                    "base_similarity": round(result.base_similarity, 6),
                    "proven": result.candidate.proven,
                    "contract_complete": result.candidate.contract.complete,
                    "normal_files": [path.name for path in result.candidate.contract.normal_files],
                    "component_scores": {
                        key: round(value, 6)
                        for key, value in result.component_scores.items()
                    },
                    "warnings": list(result.warnings),
                    "notes": result.candidate.notes,
                }
                for index, result in enumerate(results, start=1)
            ],
        }
        temporary = output_path.with_suffix(output_path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(output_path)
        return output_path

    @staticmethod
    def save_selection(
        output_path: str | Path,
        selection: HairSelection,
    ) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = output_path.with_suffix(output_path.suffix + ".tmp")
        temporary.write_text(
            json.dumps({"schema_version": 1, **selection.to_dict()}, indent=2),
            encoding="utf-8",
        )
        temporary.replace(output_path)
        return output_path
