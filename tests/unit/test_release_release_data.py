import datetime
import json
from pathlib import Path
from typing import cast

import pytest

from cfengine_cli.release.metadata import ReleasesData, VersionDocument
from cfengine_cli.release.plan import PlannedFile
from cfengine_cli.release.release_data import (
    check_upload_tools,
    publish_release_data,
    write_release_data,
)
from cfengine_cli.utils import UserError

TODAY = datetime.date(2027, 6, 1)


def _setup(tmp_path: Path) -> tuple[list[PlannedFile], Path]:
    source = tmp_path / "cfengine-masterfiles-3.30.0-1.pkg.tar.gz"
    _ = source.write_bytes(b"tarball")
    planned = [
        PlannedFile(
            source,
            source,
            "url",
            "Additional Assets",
            "Masterfiles ready-to-install tarball",
            "no arch",
            "!any",
            None,
        )
    ]
    directory = tmp_path / "out" / "release-data" / "community"
    directory.mkdir(parents=True)
    _ = (directory / "releases.json").write_text('{"lts_branches": [], "releases": []}')
    return planned, directory


def test_write_release_data(tmp_path: Path) -> None:
    planned, directory = _setup(tmp_path)
    write_release_data(
        "community",
        "3.30.0",
        "3.30.x",
        False,
        planned,
        str(tmp_path / "out"),
        dry_run=False,
        today=TODAY,
    )
    text = (directory / "3.30.0.json").read_text()
    document = cast(VersionDocument, json.loads(text))
    assert document["version"] == "3.30.0 LTS"
    assert list(document["artifacts"]) == ["Additional Assets"]
    text = (directory / "releases.json").read_text()
    releases = cast(ReleasesData, json.loads(text))
    assert [r["version"] for r in releases["releases"]] == ["3.30.0"]


def test_write_release_data_dry_run(tmp_path: Path) -> None:
    planned, directory = _setup(tmp_path)
    write_release_data(
        "community",
        "3.30.0",
        "3.30.x",
        False,
        planned,
        str(tmp_path / "out"),
        dry_run=True,
        today=TODAY,
    )
    assert not (directory / "3.30.0.json").exists()
    assert (directory / "releases.json").read_text() == (
        '{"lts_branches": [], "releases": []}'
    )


def test_check_upload_tools_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(UserError, match="Upload tool not found: aws"):
        check_upload_tools()


def test_publish_release_data_not_released(tmp_path: Path) -> None:
    with pytest.raises(UserError, match="run cfengine dev release first"):
        _ = publish_release_data(str(tmp_path), dry_run=True)
