import datetime
import os

from cfengine_cli.release.build_output import read_build_output
from cfengine_cli.release.checksums import verify_build_output
from cfengine_cli.release.plan import PlannedFile, plan_release
from cfengine_cli.release.publish import check_disk_space, publish
from cfengine_cli.release.release_data import (
    check_upload_tools,
    upload_release_data,
    write_release_data,
)
from cfengine_cli.release.utils import exit_on_sigterm
from cfengine_cli.utils import UserError


def release(
    project: str,
    version: str,
    branch: str,
    input_dir: str,
    output_dir: str,
    debug: bool,
    sign: bool,
    upload: bool,
    dry_run: bool,
) -> int:
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
        sign,
        upload,
        dry_run,
    )

    # Before any work, so a release does not fail at the very end
    if upload:
        check_upload_tools()

    build = read_build_output(input_dir)
    verify_build_output(build)

    planned = plan_release(project, version, build, input_dir, output_dir, debug)
    _print_plan(planned)

    check_disk_space(planned, output_dir)
    publish(planned, output_dir, sign_packages=sign, dry_run=dry_run)
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
    if upload:
        upload_release_data(output_dir, dry_run=dry_run)
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
    sign: bool,
    upload: bool,
    dry_run: bool,
) -> None:
    print(f"Releasing {project} {version} (branch {branch})")
    print(f"  input:  {input_dir}")
    print(f"  output: {output_dir}")
    print(f"  debug:  {debug}")
    print(f"  dry run: {dry_run}")

    steps = [
        ("sign packages", sign),
        ("upload metadata", upload),
    ]
    for name, enabled in steps:
        print(f"  {name}: {'yes' if enabled else 'skipped'}")
