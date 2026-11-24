import shutil
from pathlib import Path

from cfengine_cli.release.plan import PlannedFile
from cfengine_cli.release.utils import SIGNED_SUFFIXES, check_signing_tools, copy_file
from cfengine_cli.utils import UserError

# Free space to keep on top of the files to copy, as in the legacy release.py
DISK_SPACE_MARGIN = 1024**3


def _to_copy(planned: list[PlannedFile]) -> list[PlannedFile]:
    """Return the files with a destination that does not exist yet."""
    return [
        file
        for file in planned
        if file.destination is not None and not file.destination.exists()
    ]


def _existing_parent(path: Path) -> Path:
    while not path.exists():
        path = path.parent
    return path


def check_disk_space(planned: list[PlannedFile], output_dir: str) -> None:
    """Fail unless output_dir fits the files to copy, plus a margin."""
    sources = [file.source for file in _to_copy(planned)]
    if not sources:
        return
    needed = sum(source.stat().st_size for source in sources) + DISK_SPACE_MARGIN
    # The output dir may not exist yet, e.g. locally
    free = shutil.disk_usage(_existing_parent(Path(output_dir))).free
    if free < needed:
        raise UserError(
            (
                f"Not enough disk space in '{output_dir}': "
                f"need ~{needed // 1024**2} MiB, only {free // 1024**2} MiB free"
            )
        )


def publish(planned: list[PlannedFile], *, sign_packages: bool, dry_run: bool) -> None:
    """Copy the planned files to their destinations, signing .rpm and .deb.

    Existing destinations are skipped, so a failed run can be resumed. Files
    without a destination (debug releases) are not copied.
    """
    to_sign = [
        file for file in _to_copy(planned) if file.source.name.endswith(SIGNED_SUFFIXES)
    ]
    if sign_packages and to_sign:
        check_signing_tools()

    for file in planned:
        destination = file.destination
        if destination is None:
            continue
        if destination.exists():
            # Already published, e.g. by an earlier run that failed later on
            print(f"Warning: Skipped existing '{destination}'")
            continue
        signed = sign_packages and file.source.name.endswith(SIGNED_SUFFIXES)

        if dry_run:
            print(f"Would have copied '{file.source}' to '{destination}'")
            if signed:
                print(f"Would have signed '{destination}'")
            continue

        copy_file(file.source, destination, signed)
        print(
            f"Copied '{file.source}' to '{destination}'{' and signed' if signed else ''}"
        )
