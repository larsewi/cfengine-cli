import datetime
import json
import shutil
import urllib.request
from http.client import HTTPResponse
from pathlib import Path
from typing import cast

from cfengine_cli.release.metadata import (
    ReleasesData,
    VersionDocument,
    build_artifacts,
    release_data_url,
    update_releases,
    version_document,
)
from cfengine_cli.release.plan import PlannedFile
from cfengine_cli.release.utils import atomic_write, run
from cfengine_cli.utils import UserError

# Uploaded to release-data on S3, like the legacy release.py does
RELEASE_DATA_DIR = "release-data"
S3_RELEASE_DATA = "s3://cfengine-package-repos/release-data"


def _read_releases(path: Path, project: str) -> ReleasesData:
    """Read releases.json, or fetch the published one if there is none yet."""
    if path.exists():
        return cast(ReleasesData, json.loads(path.read_text()))
    url = release_data_url(project, "releases")
    print(f"No '{path}', fetching '{url}'")
    try:
        # urlopen() is typed Any, but returns this for http(s) URLs
        response = cast(HTTPResponse, urllib.request.urlopen(url, timeout=60))
        with response:
            return cast(ReleasesData, json.load(response))
    except OSError as e:
        # Unlike the legacy release.py, do not start from an empty list. It
        # would replace the published releases.json once uploaded.
        raise UserError(f"Could not fetch '{url}': {e}") from e


def _write_json(
    path: Path,
    data: ReleasesData | VersionDocument,
    output_dir: str,
    *,
    dry_run: bool,
) -> None:
    if dry_run:
        print(f"Would have written '{path}'")
        return
    with atomic_write(path, output_dir) as temporary:
        # Same format as the legacy release.py
        _ = temporary.write_text(json.dumps(data, indent=4))
    print(f"Wrote '{path}'")


def write_release_data(
    project: str,
    version: str,
    branch: str,
    debug: bool,
    planned: list[PlannedFile],
    output_dir: str,
    *,
    dry_run: bool,
    today: datetime.date,
) -> None:
    """Write release-data/<project>/<version>.json and update releases.json."""
    directory = Path(output_dir) / RELEASE_DATA_DIR / project
    releases_path = directory / "releases.json"

    artifacts, footnotes = build_artifacts(planned, dry_run)
    document = version_document(project, version, branch, artifacts, footnotes, today)
    releases = update_releases(
        _read_releases(releases_path, project), project, version, branch, debug, today
    )

    # The document first, so releases.json never links to a missing one
    _write_json(directory / f"{version}.json", document, output_dir, dry_run=dry_run)
    _write_json(releases_path, releases, output_dir, dry_run=dry_run)


def check_upload_tools() -> None:
    if shutil.which("aws") is None:
        raise UserError("Upload tool not found: aws")


def upload_release_data(output_dir: str, *, dry_run: bool) -> None:
    """Upload release-data to S3, as the legacy release.py does."""
    directory = Path(output_dir) / RELEASE_DATA_DIR
    if dry_run:
        print(f"Would have uploaded '{directory}' to '{S3_RELEASE_DATA}'")
        return
    output = run(
        [
            "aws",
            "s3",
            "sync",
            str(directory),
            S3_RELEASE_DATA,
            "--acl",
            "public-read",
        ]
    )
    print(output, end="")
    print(f"Uploaded '{directory}' to '{S3_RELEASE_DATA}'")
