import datetime
import os
import signal
import sys
from types import FrameType
from typing import NoReturn

from cfengine_cli.release.build_output import BuildOutput, read_build_output
from cfengine_cli.release.checksums import verify_checksums
from cfengine_cli.release.plan import PlannedFile, plan_assets, plan_packages
from cfengine_cli.release.publish import check_disk_space, publish
from cfengine_cli.release.release_data import (
    check_upload_tools,
    upload_release_data,
    write_release_data,
)
from cfengine_cli.release.repo import RepoFile, plan_repo, update_repos
from cfengine_cli.utils import UserError


def _exit_on_sigterm(_signum: int, _frame: FrameType | None) -> NoReturn:
    sys.exit(1)


def release(
    project: str,
    version: str,
    branch: str,
    input_dir: str,
    output_dir: str,
    debug: bool,
    sign: bool,
    update_repo: bool,
    upload: bool,
    dry_run: bool,
) -> int:
    if not os.path.isdir(input_dir):
        raise UserError(f"Input directory '{input_dir}' does not exist")

    # Exit cleanly on SIGTERM, e.g. an aborted Jenkins job, so temporary
    # files are removed
    _ = signal.signal(signal.SIGTERM, _exit_on_sigterm)

    _print_summary(
        project,
        version,
        branch,
        input_dir,
        output_dir,
        debug,
        sign,
        update_repo,
        upload,
        dry_run,
    )

    # Before any work, so a release does not fail at the very end
    if upload:
        check_upload_tools()

    build = read_build_output(input_dir)
    _verify_build_output(build)

    planned = _plan(project, version, build, input_dir, output_dir, debug)
    _print_plan(planned)
    # Only community has repos
    repo_files: list[RepoFile] = []
    if update_repo and project == "community":
        repo_files = plan_repo(planned, output_dir)
        _print_repo_plan(repo_files)

    check_disk_space(planned, output_dir)
    publish(planned, output_dir, sign_packages=sign, dry_run=dry_run)
    update_repos(repo_files, output_dir, dry_run=dry_run)
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


def _plan(
    project: str,
    version: str,
    build: BuildOutput,
    input_dir: str,
    output_dir: str,
    debug: bool,
) -> list[PlannedFile]:
    """Plan every file to publish: platform packages, then additional assets."""
    return plan_packages(
        project, version, build, input_dir, output_dir, debug
    ) + plan_assets(project, version, build, input_dir, output_dir, debug)


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


def _print_repo_plan(repo_files: list[RepoFile]) -> None:
    print(f"Planned {len(repo_files)} repository files:")
    for file in repo_files:
        print(f"  {file.destination.name}")
        print(f"    from: {file.source}")
        print(f"    to:   {file.destination}")


def _verify_build_output(build: BuildOutput) -> None:
    output_dirs = [*build.labels.values(), build.tarballs]
    if build.vagrant is not None:
        output_dirs.append(build.vagrant)
    for output_dir in output_dirs:
        verify_checksums(output_dir.sha256sums)
    print("Checksums OK")


def _print_summary(
    project: str,
    version: str,
    branch: str,
    input_dir: str,
    output_dir: str,
    debug: bool,
    sign: bool,
    update_repo: bool,
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
        ("update repositories", update_repo and project == "community"),
        ("upload metadata", upload),
    ]
    for name, enabled in steps:
        print(f"  {name}: {'yes' if enabled else 'skipped'}")
