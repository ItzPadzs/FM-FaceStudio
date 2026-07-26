from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class SkinCandidate:
    skin_path: str
    player_id: str
    score: int
    face_png: str | None
    cfg2_path: str | None
    hair_skin: str | None
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class SkinLibraryResult:
    roots_scanned: tuple[str, ...]
    skin_count: int
    candidates: tuple[SkinCandidate, ...]
    warnings: tuple[str, ...]


class AutoSkinFinder:
    """Locate loose FM26 SKIN files and rank complete research candidates.

    Ranking is evidence-based only. Until SKIN geometry is decoded, FaceStudio
    cannot honestly compare 3D facial shape. Candidates score higher when the
    same numeric ID also has a face PNG, CFG2 and hair assets because those sets
    are more useful for controlled research and texture transfer.
    """

    def discover_roots(self, explicit_root: Path | None = None) -> tuple[Path, ...]:
        roots: list[Path] = []
        if explicit_root is not None:
            roots.append(explicit_root.expanduser())
        env_root = os.environ.get("FM26_HEADS_DIR")
        if env_root:
            roots.append(Path(env_root).expanduser())
        roots.extend([
            Path(r"C:\Program Files (x86)\Steam\steamapps\common\Football Manager 26\heads"),
            Path(r"C:\Program Files\Steam\steamapps\common\Football Manager 26\heads"),
            Path.home() / "Downloads" / "FaceStudio Facepack" / "faces2",
        ])
        unique: list[Path] = []
        seen: set[str] = set()
        for root in roots:
            key = str(root).lower()
            if key not in seen and root.is_dir():
                seen.add(key)
                unique.append(root.resolve())
        return tuple(unique)

    def scan(self, explicit_root: Path | None = None, limit: int = 50) -> SkinLibraryResult:
        roots = self.discover_roots(explicit_root)
        warnings: list[str] = []
        if not roots:
            raise ValueError("No FM26 heads folder was found automatically. Choose one manually.")
        candidates: list[SkinCandidate] = []
        skin_count = 0
        for root in roots:
            try:
                files = list(root.rglob("*.skin"))
            except OSError as exc:
                warnings.append(f"Could not scan {root}: {exc}")
                continue
            skin_count += len(files)
            for skin in files:
                stem = skin.stem
                if stem.endswith("_hair"):
                    continue
                player_id = stem.split("_", 1)[0]
                if not player_id.isdigit():
                    continue
                folder = skin.parent
                face = folder / f"{player_id}.png"
                cfg2 = folder / f"{player_id}.cfg2"
                hair = folder / f"{player_id}_hair.skin"
                score = 40
                reasons = ["numeric-ID SKIN found"]
                if face.is_file():
                    score += 30
                    reasons.append("matching face PNG")
                if cfg2.is_file():
                    score += 20
                    reasons.append("matching CFG2")
                if hair.is_file():
                    score += 10
                    reasons.append("matching hair SKIN")
                candidates.append(SkinCandidate(
                    skin_path=str(skin), player_id=player_id, score=score,
                    face_png=str(face) if face.is_file() else None,
                    cfg2_path=str(cfg2) if cfg2.is_file() else None,
                    hair_skin=str(hair) if hair.is_file() else None,
                    reasons=tuple(reasons),
                ))
        candidates.sort(key=lambda item: (-item.score, item.player_id, item.skin_path.lower()))
        return SkinLibraryResult(
            roots_scanned=tuple(str(root) for root in roots),
            skin_count=skin_count,
            candidates=tuple(candidates[:max(1, limit)]),
            warnings=tuple(warnings),
        )
