import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from cfengine_cli.release.build_output import read_build_output
from cfengine_cli.release.checksums import verify_build_output
from cfengine_cli.release.plan import PlannedFile, plan_release
from cfengine_cli.release.utils import (
    check_disk_space,
    copy_file,
    exit_on_sigterm,
    is_signed_rpm,
    run,
)
from cfengine_cli.utils import UserError

# The community repos, shared by all branches. The legacy release.py, still
# used for LTS releases, writes to the same repos with the same settings.
REPO_DIR = "repo"
APT_POOL = "apt/packages/pool/main/C"
# Labels whose packages go into the repos, as in the legacy release.py
APT_LABELS = ("PACKAGES_x86_64_linux_debian_12", "PACKAGES_arm_64_linux_debian_12")
YUM_LABELS = {
    "PACKAGES_x86_64_linux_redhat_7": "x86_64",
    "PACKAGES_x86_64_linux_redhat_8": "x86_64",
    "PACKAGES_arm_64_linux_redhat_8": "aarch64",
    "PACKAGES_x86_64_linux_redhat_9": "x86_64",
    "PACKAGES_arm_64_linux_redhat_9": "aarch64",
    "PACKAGES_x86_64_linux_redhat_10": "x86_64",
    "PACKAGES_arm_64_linux_redhat_10": "aarch64",
}
# Signs the APT Release file
RELEASE_KEY = "contact@northern.tech"
REPO_TOOLS = ("apt-ftparchive", "createrepo_c", "gpg", "rpm")

# The settings of apt-ftparchive.conf in infra, with paths from the repo dir.
# i386 is kept, as the pool still has old i386 packages.
APT_FTPARCHIVE_CONF = """\
Dir {{
   ArchiveDir "{apt}/packages";
   CacheDir   "{apt}/cache/";
}};


Default {{
   Packages::Compress ". gzip bzip2";
   Sources::Compress  ". gzip bzip2";
   Contents::Compress ". gzip bzip2";
}};


TreeDefault {{
   BinCacheDB   "packages-$(SECTION)-$(ARCH).db";
   Directory    "pool/$(SECTION)";
   SrcDirectory "pool/$(SECTION)";
   Packages     "$(DIST)/$(SECTION)/binary-$(ARCH)/Packages";
   Sources      "$(DIST)/$(SECTION)/source/Sources";
   Contents     "$(DIST)/Contents-$(ARCH)";
}};


Tree "dists/stable" {{
    Sections "main";
    Architectures "i386 amd64 arm64";
}}
"""

# The settings of apt-ftparchiveRelease.conf in infra
APT_FTPARCHIVE_RELEASE_CONF = """\
APT::FTPArchive::Release::Codename   "community";
APT::FTPArchive::Release::Origin     "CFEngine";
APT::FTPArchive::Release::Components "main";
APT::FTPArchive::Release::Label      "Official packages";
APT::FTPArchive::Release::Architectures "i386 amd64 arm64";
APT::FTPArchive::Release::Suite         "stable";
"""


@dataclass(frozen=True)
class RepoFile:
    """A package to add to a repo."""

    source: Path
    destination: Path


def plan_repo(planned: list[PlannedFile], output_dir: str) -> list[RepoFile]:
    """Plan the packages to add to the community repos."""
    repo = Path(output_dir) / REPO_DIR
    files: list[RepoFile] = []
    for file in planned:
        # Debug releases publish nothing
        if file.destination is None or file.package is None:
            continue
        if file.package in APT_LABELS and file.source.name.endswith(".deb"):
            # The unsigned build, as in the legacy release.py. apt trusts the
            # signed Release file instead.
            files.append(RepoFile(file.source, repo / APT_POOL / file.source.name))
        elif file.package in YUM_LABELS and file.source.name.endswith(".rpm"):
            # The signed copy in the release dir
            yum_dir = repo / "yum" / YUM_LABELS[file.package]
            files.append(RepoFile(file.destination, yum_dir / file.destination.name))
    return files


def _check_repo_tools() -> None:
    missing = [tool for tool in REPO_TOOLS if shutil.which(tool) is None]
    if missing:
        raise UserError(f"Repository tools not found: {', '.join(missing)}")


def _update_apt(apt: Path) -> None:
    """Regenerate and sign the APT metadata, as update-apt-repo.sh in infra."""
    stable = apt / "packages/dists/stable"
    for directory in (
        apt / "cache",
        apt / "packages/pool/main",
        stable / "main/binary-amd64",
        stable / "main/binary-i386",
        stable / "main/binary-arm64",
        stable / "main/source",
    ):
        directory.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        conf = Path(tmp) / "apt-ftparchive.conf"
        _ = conf.write_text(APT_FTPARCHIVE_CONF.format(apt=apt))
        release_conf = Path(tmp) / "apt-ftparchiveRelease.conf"
        _ = release_conf.write_text(APT_FTPARCHIVE_RELEASE_CONF)
        _ = run(["apt-ftparchive", "generate", str(conf)])
        release = run(
            ["apt-ftparchive", "-c", str(release_conf), "release", str(stable)]
        )
    _ = (stable / "Release").write_text(release)

    gpg = ["gpg", "--yes", "--armor", "--digest-algo=SHA256"]
    gpg += ["--default-key", RELEASE_KEY]
    release_file = str(stable / "Release")
    _ = run([*gpg, "--detach-sign", "--output", f"{release_file}.gpg", release_file])
    # The same signature embedded, the modern way
    _ = run([*gpg, "--clearsign", "--output", str(stable / "InRelease"), release_file])


def _update_yum(directory: Path) -> None:
    """Regenerate and sign the YUM metadata of one arch."""
    _ = run(["createrepo_c", "--simple-md-filenames", str(directory)])
    _ = run(
        [
            "gpg",
            "--yes",
            "--armor",
            "--detach-sign",
            str(directory / "repodata/repomd.xml"),
        ]
    )


def update_repo(version: str, input_dir: str, output_dir: str, *, dry_run: bool) -> int:
    """Add a community release to the repos, after cfengine dev release."""
    if not os.path.isdir(input_dir):
        raise UserError(f"Input directory '{input_dir}' does not exist")
    exit_on_sigterm()

    print(f"Updating the community repositories with {version}")
    print(f"  input:  {input_dir}")
    print(f"  output: {output_dir}")
    print(f"  dry run: {dry_run}")

    build = read_build_output(input_dir)
    verify_build_output(build)
    planned = plan_release("community", version, build, input_dir, output_dir, False)
    files = plan_repo(planned, output_dir)
    _print_repo_plan(files)
    update_repos(files, output_dir, dry_run=dry_run)
    return 0


def _print_repo_plan(files: list[RepoFile]) -> None:
    print(f"Planned {len(files)} repository files:")
    for file in files:
        print(f"  {file.destination.name}")
        print(f"    from: {file.source}")
        print(f"    to:   {file.destination}")


def update_repos(files: list[RepoFile], output_dir: str, *, dry_run: bool) -> None:
    """Add the planned packages to the repos, and regenerate their metadata.

    The metadata is regenerated from all packages in the repo, so a failed
    run is repaired by running again.
    """
    if not files:
        return
    missing = [str(file.source) for file in files if not file.source.exists()]
    if missing:
        raise UserError(
            f"Not found, run cfengine dev release first: {', '.join(missing)}"
        )
    _check_repo_tools()
    # E.g. released with --no-sign. yum clients with gpgcheck would fail.
    unsigned = [
        str(file.source)
        for file in files
        if file.source.name.endswith(".rpm") and not is_signed_rpm(file.source)
    ]
    if unsigned:
        raise UserError(f"Not signed, cannot add to the repo: {', '.join(unsigned)}")
    check_disk_space([(f.source, f.destination) for f in files], output_dir)

    for file in files:
        if file.destination.exists():
            # Already added, e.g. by an earlier run that failed later on
            print(f"Warning: Skipped existing '{file.destination}'")
            continue
        if dry_run:
            print(f"Would have copied '{file.source}' to '{file.destination}'")
            continue
        copy_file(file.source, file.destination, output_dir, signed=False)
        print(f"Copied '{file.source}' to '{file.destination}'")

    repo = Path(output_dir) / REPO_DIR
    apt = any(file.destination.name.endswith(".deb") for file in files)
    yum_dirs = sorted(
        {file.destination.parent for file in files if file.destination.suffix == ".rpm"}
    )
    if apt:
        if dry_run:
            print(f"Would have updated the APT repo in '{repo / 'apt'}'")
        else:
            _update_apt(repo / "apt")
            print(f"Updated the APT repo in '{repo / 'apt'}'")
    for yum_dir in yum_dirs:
        if dry_run:
            print(f"Would have updated the YUM repo in '{yum_dir}'")
        else:
            _update_yum(yum_dir)
            print(f"Updated the YUM repo in '{yum_dir}'")
