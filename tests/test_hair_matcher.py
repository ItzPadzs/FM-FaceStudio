from __future__ import annotations

from pathlib import Path
import struct
import zipfile

from facestudio.hair.export import build_native_hair_package
from facestudio.hair.library import HairLibrary
from facestudio.hair.matcher import HairMatcher
from facestudio.hair.skin import describe_hair_skin, read_fm26_hair_skin


def write_hair(path: Path, positions: list[tuple[float, float, float]], indices: list[int]) -> None:
    out = bytearray(struct.pack('<III', len(positions), len(indices), 0))
    for i, (x, y, z) in enumerate(positions):
        out += struct.pack('<8f', x, y, z, 0.0, 1.0, 0.0, (i % 2), ((i // 2) % 2))
    out += struct.pack(f'<{len(indices)}I', *indices)
    path.write_bytes(out)


def make_set(root: Path, uid: str, positions: list[tuple[float, float, float]], normal2: bool = True) -> Path:
    folder = root / uid
    folder.mkdir(parents=True)
    skin = folder / f'{uid}_hair.skin'
    write_hair(skin, positions, [0, 1, 2, 0, 2, 3])
    (folder / f'{uid}_hair2.png').write_bytes(b'PNG-DIFFUSE-' + uid.encode())
    if normal2:
        (folder / f'{uid}_hair2_nrm.png').write_bytes(b'PNG-NRM2-' + uid.encode())
    else:
        (folder / f'{uid}_hair_nrm.png').write_bytes(b'PNG-NRM-' + uid.encode())
    (folder / f'{uid}.cfg2').write_text('eye_s=1\nhair_at=0.395\nhair_tile=3.0\n', encoding='utf-8')
    return skin


def test_parser_and_exact_match_rank_first(tmp_path: Path) -> None:
    target_points = [(-1, 0, 0), (1, 0, 0), (1, 2, 1), (-1, 2, 1)]
    wrong_points = [(-2, 0, 0), (2, 0, 0), (2, 0.5, 0.3), (-2, 0.5, 0.3)]
    target_skin = make_set(tmp_path / 'library', '100', target_points)
    make_set(tmp_path / 'library', '200', wrong_points)

    mesh = read_fm26_hair_skin(target_skin)
    assert mesh.vertex_count == 4
    assert mesh.triangle_count == 2

    library = HairLibrary()
    candidates = library.scan(tmp_path / 'library')
    target = describe_hair_skin(target_skin)
    ranked = HairMatcher().rank(target, candidates, limit=None)
    assert ranked[0].candidate.contract.uid == '100'
    assert ranked[0].similarity > ranked[1].similarity


def test_contract_keeps_native_normal_filename(tmp_path: Path) -> None:
    make_set(tmp_path / 'library', '300', [(-1, 0, 0), (1, 0, 0), (1, 2, 1), (-1, 2, 1)], normal2=True)
    candidate = HairLibrary().scan(tmp_path / 'library')[0]
    assert candidate.contract.normal is None
    assert candidate.contract.normal2 is not None
    assert candidate.contract.normal2.name == '300_hair2_nrm.png'


def test_export_is_byte_locked_and_creates_no_alias(tmp_path: Path) -> None:
    make_set(tmp_path / 'library', '400', [(-1, 0, 0), (1, 0, 0), (1, 2, 1), (-1, 2, 1)], normal2=True)
    candidate = HairLibrary().scan(tmp_path / 'library')[0]
    output = build_native_hair_package(candidate, '999', tmp_path / 'hair.zip')
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        assert '999/999_hair.skin' in names
        assert '999/999_hair2.png' in names
        assert '999/999_hair2_nrm.png' in names
        assert '999/999_hair_nrm.png' not in names
        assert archive.read('999/999_hair.skin') == candidate.contract.skin.read_bytes()
        assert archive.read('999/999_hair2.png') == candidate.contract.diffuse.read_bytes()
        assert archive.read('999/999_hair2_nrm.png') == candidate.contract.normal2.read_bytes()
