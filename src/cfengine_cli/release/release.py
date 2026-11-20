import os

from cfengine_cli.utils import UserError


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
    return 0


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
