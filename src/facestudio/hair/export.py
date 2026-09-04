from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import zipfile

from facestudio.hair.models import HairCandidate


_HAIR_MATERIAL = re.compile(
    r"^\s*(hair_(?:at|tile|color|emis|smoothness))\s*=\s*(.*?)\s*$",
    re.IGNORECASE,
)


def _digest(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_hair_material_contract(cfg2: Path | None) -> list[str]:
    if cfg2 is None or not cfg2.is_file():
        return []
    lines: list[str] = []
    for raw in cfg2.read_text(encoding="utf-8", errors="replace").splitlines():
        match = _HAIR_MATERIAL.match(raw)
        if match:
            lines.append(f"{match.group(1).lower()}={match.group(2)}")
    return lines


def build_native_hair_package(
    candidate: HairCandidate,
    target_uid: str,
    output_zip: str | Path,
) -> Path:
    """Build an untouched cross-UID native-hair package.

    Only filenames change.  Every source asset byte is copied exactly.  A cfg2
    fragment is supplied separately instead of overwriting the target face cfg2.
    """

    uid = str(target_uid).strip()
    if not uid or any(ch in uid for ch in '<>:"/\\|?*'):
        raise ValueError("target UID is empty or contains invalid filename characters")
    if not candidate.contract.complete:
        raise ValueError("selected donor hair does not contain a complete skin + diffuse contract")

    output_zip = Path(output_zip)
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    staging = output_zip.parent / f".{output_zip.stem}.staging"
    if staging.exists():
        shutil.rmtree(staging)
    target_root = staging / uid
    target_root.mkdir(parents=True)

    mapping: list[tuple[Path, Path]] = [
        (candidate.contract.skin, target_root / f"{uid}_hair.skin"),
        (candidate.contract.diffuse, target_root / f"{uid}_hair2.png"),
    ]
    if candidate.contract.normal is not None:
        mapping.append((candidate.contract.normal, target_root / f"{uid}_hair_nrm.png"))
    if candidate.contract.normal2 is not None:
        mapping.append((candidate.contract.normal2, target_root / f"{uid}_hair2_nrm.png"))

    files: dict[str, dict[str, object]] = {}
    for source, destination in mapping:
        shutil.copyfile(source, destination)
        source_hash = _digest(source)
        output_hash = _digest(destination)
        if source_hash != output_hash:
            raise RuntimeError(f"byte-lock failed while copying {source.name}")
        files[destination.name] = {
            "source": str(source),
            "sha256": output_hash,
            "byte_identical": True,
            "size": destination.stat().st_size,
        }

    material_lines = extract_hair_material_contract(candidate.contract.cfg2)
    if material_lines:
        fragment = target_root / "HAIR_MATERIAL.cfg2.fragment"
        fragment.write_text("\n".join(material_lines) + "\n", encoding="utf-8")

    report = {
        "schema_version": 1,
        "mode": "untouched_native_fm_hair_cross_uid",
        "target_uid": uid,
        "donor_uid": candidate.contract.uid,
        "donor_name": candidate.display_name,
        "candidate_id": candidate.candidate_id,
        "proven": candidate.proven,
        "contract_policy": {
            "geometry_modified": False,
            "positions_modified": False,
            "stored_normals_modified": False,
            "uvs_modified": False,
            "indices_or_winding_modified": False,
            "diffuse_modified": False,
            "normal_modified": False,
            "normal_alias_created": False,
            "texture_resized": False,
        },
        "hair_material_lines": material_lines,
        "files": files,
    }
    (target_root / "HAIR_SELECTION_REPORT.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )

    temporary_zip = output_zip.with_suffix(output_zip.suffix + ".tmp")
    with zipfile.ZipFile(temporary_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(target_root.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(staging))
    temporary_zip.replace(output_zip)
    shutil.rmtree(staging, ignore_errors=True)
    return output_zip
