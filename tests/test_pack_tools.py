from pathlib import Path

from facestudio.pack_tools.service import PackTestInstallService


def make_pack(root: Path, name: str = "Test Pack") -> Path:
    pack = root / name
    faces = pack / "faces"
    faces.mkdir(parents=True)
    (faces / "123.png").write_bytes(b"not-a-real-png-but-present")
    (pack / "config.xml").write_text(
        "<?xml version='1.0' encoding='utf-8'?>\n"
        "<record><boolean id='preload' value='false'/><boolean id='amap' value='false'/>"
        "<list id='maps'><record from='faces/123' to='graphics/pictures/person/123/portrait'/></list></record>",
        encoding="utf-8",
    )
    (pack / "facestudio-manifest.json").write_text('{"name": "Test Pack"}', encoding="utf-8")
    return pack


def test_validate_complete_pack(tmp_path: Path) -> None:
    service = PackTestInstallService(tmp_path / "data")
    report = service.validate_pack(make_pack(tmp_path))
    assert report.valid
    assert report.mapping_count == 1
    assert report.image_count == 1


def test_validate_reports_missing_mapped_image(tmp_path: Path) -> None:
    service = PackTestInstallService(tmp_path / "data")
    pack = make_pack(tmp_path)
    (pack / "faces" / "123.png").unlink()
    report = service.validate_pack(pack)
    assert not report.valid
    assert any("Mapped image is missing" in issue for issue in report.issues)


def test_dry_run_does_not_copy_files(tmp_path: Path) -> None:
    service = PackTestInstallService(tmp_path / "data")
    pack = make_pack(tmp_path)
    graphics = tmp_path / "graphics"
    actions = service.dry_run(pack, graphics)
    assert any("Copy pack" in action for action in actions)
    assert not graphics.exists()


def test_install_and_verify(tmp_path: Path) -> None:
    service = PackTestInstallService(tmp_path / "data")
    pack = make_pack(tmp_path / "source")
    graphics = tmp_path / "graphics"
    result = service.install(pack, graphics)
    target = Path(str(result["target"]))
    assert target.is_dir()
    assert (target / "facestudio-install.json").is_file()
    assert service.verify_installed(target).valid


def test_existing_install_is_backed_up(tmp_path: Path) -> None:
    service = PackTestInstallService(tmp_path / "data")
    pack = make_pack(tmp_path / "source")
    graphics = tmp_path / "graphics"
    existing = make_pack(graphics)
    (existing / "old.txt").write_text("old", encoding="utf-8")
    result = service.install(pack, graphics)
    backup = Path(str(result["backup"]))
    assert backup.is_dir()
    assert (backup / "old.txt").is_file()
