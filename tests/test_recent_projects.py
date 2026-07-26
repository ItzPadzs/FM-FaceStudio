from pathlib import Path

from facestudio.projects.recent import RecentProject, RecentProjectsStore


def test_recent_projects_are_deduplicated(tmp_path: Path) -> None:
    store = RecentProjectsStore(tmp_path / "recent.json", limit=10)
    project = RecentProject("Player One", str(tmp_path / "one.facestudio"))

    store.add(project)
    store.add(project)

    assert store.load() == [project]


def test_recent_projects_limit(tmp_path: Path) -> None:
    store = RecentProjectsStore(tmp_path / "recent.json", limit=2)
    store.add(RecentProject("One", "one"))
    store.add(RecentProject("Two", "two"))
    store.add(RecentProject("Three", "three"))

    assert [item.name for item in store.load()] == ["Three", "Two"]
