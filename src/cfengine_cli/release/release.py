import os

from cfengine_cli.release.build_output import read_build_output
from cfengine_cli.release.checksums import verify_build_output
from cfengine_cli.release.metadata import is_nightly, release_branch
from cfengine_cli.utils import UserError


def release(
    project: str,
    version: str,
    input_dir: str,
    output_dir: str,
    dry_run: bool,
) -> int:
    branch = release_branch(project, version)
    # Nightlies are debug releases causing them to be hidden from the downloads page
    debug = is_nightly(version)
    if not os.path.isdir(input_dir):
        raise UserError(f"Input directory '{input_dir}' does not exist")

    _print_summary(
        project,
        version,
        branch,
        input_dir,
        output_dir,
        debug,
        dry_run,
    )

    build = read_build_output(input_dir)
    verify_build_output(build)
    return 0


def _print_summary(
    project: str,
    version: str,
    branch: str,
    input_dir: str,
    output_dir: str,
    debug: bool,
    dry_run: bool,
) -> None:
    print(f"Releasing {project} {version} (branch {branch})")
    print(f"  input:  {input_dir}")
    print(f"  output: {output_dir}")
    print(f"  debug:  {debug}")
    print(f"  dry run: {dry_run}")
