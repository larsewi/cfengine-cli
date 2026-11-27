from cfengine_cli.release.plan import PlannedFile
from cfengine_cli.release.utils import SIGNED_SUFFIXES, check_tools, copy_file

SIGNING_TOOLS = ("rpm", "rpmsign", "debsigs")


def _to_copy(planned: list[PlannedFile]) -> list[PlannedFile]:
    """Return the files with a destination that does not exist yet."""
    return [
        file
        for file in planned
        if file.destination is not None and not file.destination.exists()
    ]


def publish(
    planned: list[PlannedFile], output_dir: str, *, sign_packages: bool, dry_run: bool
) -> None:
    """Copy the planned files to their destinations, signing .rpm and .deb.

    Existing destinations are skipped, so a failed run can be resumed. Files
    without a destination (debug releases) are not copied.
    """
    to_sign = [
        file for file in _to_copy(planned) if file.source.name.endswith(SIGNED_SUFFIXES)
    ]
    if sign_packages and to_sign:
        check_tools("Signing", SIGNING_TOOLS)

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

        copy_file(file.source, destination, output_dir, signed=signed)
        print(
            f"Copied '{file.source}' to '{destination}'{' and signed' if signed else ''}"
        )
