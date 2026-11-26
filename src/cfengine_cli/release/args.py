import argparse


def add_release_args(sp: argparse.ArgumentParser) -> None:
    _ = sp.add_argument(
        "--project",
        required=True,
        choices=["enterprise", "community"],
        help="Which edition to release",
    )
    _ = sp.add_argument(
        "--version",
        required=True,
        help="Version to release, e.g. 3.30.0, or 3.30.x / master for nightlies",
    )
    _ = sp.add_argument(
        "--branch",
        required=True,
        help="Branch the release belongs to, e.g. 3.30.x or nightly-master",
    )
    _ = sp.add_argument(
        "--debug",
        action="store_true",
        help="Mark as a debug release, not shown on the downloads page",
    )
    _ = sp.add_argument(
        "--input",
        required=True,
        help="Directory with the build output, one subdirectory per label",
    )
    _ = sp.add_argument(
        "--output",
        required=True,
        help="Root directory to write release/ and release-data/ to",
    )
    _ = sp.add_argument(
        "--no-sign", action="store_true", help="Don't sign the packages"
    )
    _ = sp.add_argument(
        "--dry-run", action="store_true", help="Only print what would be done"
    )


def add_publish_args(sp: argparse.ArgumentParser) -> None:
    _ = sp.add_argument(
        "--output",
        required=True,
        help="Root directory with release/, repo/ and release-data/",
    )
    _ = sp.add_argument(
        "--bucket",
        required=True,
        choices=["test", "prod"],
        help="test: only the repos, to try them. prod: everything, release data last",
    )
    _ = sp.add_argument(
        "--release-data-only",
        action="store_true",
        help="Only upload the release data, e.g. for nightlies. Needs --bucket prod",
    )
    _ = sp.add_argument(
        "--dry-run", action="store_true", help="Only list what would be uploaded"
    )


def add_update_repo_args(sp: argparse.ArgumentParser) -> None:
    _ = sp.add_argument(
        "--version",
        required=True,
        help="Community version to add, e.g. 3.30.0",
    )
    _ = sp.add_argument(
        "--input",
        required=True,
        help="Directory with the build output, as given to cfengine dev release",
    )
    _ = sp.add_argument(
        "--output",
        required=True,
        help="Root directory with release/ and repo/, as given to cfengine dev release",
    )
    _ = sp.add_argument(
        "--dry-run", action="store_true", help="Only print what would be done"
    )
