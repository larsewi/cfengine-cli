import datetime
import os

from cfengine_cli.release.build_output import read_build_output
from cfengine_cli.release.checksums import verify_build_output
from cfengine_cli.release.metadata import is_nightly, release_branch
from cfengine_cli.release.plan import PlannedFile, plan_release
from cfengine_cli.release.copy_files import copy_files
from cfengine_cli.release.release_data import write_release_data
from cfengine_cli.release.utils import (
    check_disk_space,
    exit_on_sigterm,
    output_lock,
)
from cfengine_cli.utils import UserError


def release(
    project: str,
    version: str,
    input_dir: str,
    output_dir: str,
    dry_run: bool,
) -> int:
    branch = release_branch(project, version)
    # Nightlies are debug releases, hidden from the downloads page
    debug = is_nightly(version)
    if not os.path.isdir(input_dir):
        raise UserError(f"Input directory '{input_dir}' does not exist")

    exit_on_sigterm()

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

    planned = plan_release(project, version, build, output_dir, debug)
    _print_plan(planned)

    with output_lock(output_dir, dry_run=dry_run):
        check_disk_space([(f.source, f.destination) for f in planned], output_dir)
        copy_files(planned, output_dir, dry_run=dry_run)
        write_release_data(
            project,
            version,
            branch,
            debug,
            planned,
            output_dir,
            dry_run=dry_run,
            today=datetime.date.today(),
        )
    return 0


def _print_plan(planned: list[PlannedFile]) -> None:
    print(f"Planned {len(planned)} files:")
    section = None
    for file in planned:
        if file.section != section:
            section = file.section
            print(f"  {section}")
        print(f"    {file.source.name}")
        print(f"      from: {file.source}")
        print(f"      to:   {file.destination or 'not copied'}")
        print(f"      url:  {file.url}")


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
