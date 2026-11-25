from pathlib import Path

import pytest

from cfengine_cli.release.plan import PlannedFile
from cfengine_cli.release.publish import publish
from cfengine_cli.utils import UserError


def _planned(source: Path, destination: Path | None) -> PlannedFile:
    return PlannedFile(
        source, destination, "url", "Section", "Title", "x86_64", "any", None
    )


@pytest.fixture
def rpm(tmp_path: Path) -> Path:
    source = tmp_path / "build" / "cfengine-nova-3.30.0-1.el9.x86_64.rpm"
    source.parent.mkdir()
    _ = source.write_text("built")
    return source


def test_publish(tmp_path: Path, rpm: Path) -> None:
    destination = tmp_path / "release" / rpm.name
    publish(
        [_planned(rpm, destination)], str(tmp_path), sign_packages=False, dry_run=False
    )
    assert destination.read_text() == "built"
    # No temporary dir left
    assert list(tmp_path.glob(".tmp-*")) == []


def test_publish_skips_existing(
    tmp_path: Path, rpm: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    destination = tmp_path / "release" / rpm.name
    destination.parent.mkdir()
    _ = destination.write_text("published")
    publish(
        [_planned(rpm, destination)], str(tmp_path), sign_packages=False, dry_run=False
    )
    assert destination.read_text() == "published"
    assert f"Warning: Skipped existing '{destination}'" in capsys.readouterr().out


def test_publish_skips_debug(
    tmp_path: Path, rpm: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    publish([_planned(rpm, None)], str(tmp_path), sign_packages=False, dry_run=False)
    assert capsys.readouterr().out == ""


def test_publish_dry_run(
    tmp_path: Path, rpm: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    destination = tmp_path / "release" / rpm.name
    publish(
        [_planned(rpm, destination)], str(tmp_path), sign_packages=False, dry_run=True
    )
    assert not destination.parent.exists()
    assert capsys.readouterr().out == (
        f"Would have copied '{rpm}' to '{destination}'\n"
    )


def test_publish_missing_signing_tools(
    tmp_path: Path, rpm: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))
    destination = tmp_path / "release" / rpm.name
    with pytest.raises(UserError, match="Signing tools not found"):
        publish(
            [_planned(rpm, destination)],
            str(tmp_path),
            sign_packages=True,
            dry_run=True,
        )
