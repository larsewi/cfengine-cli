from dataclasses import dataclass
from pathlib import Path

from cfengine_cli.release.build_output import BuildOutput
from cfengine_cli.release.platforms import get_platform

S3_URL = "https://cfengine-package-repos.s3.amazonaws.com"
BUILDCACHE_URL = "http://buildcache.cfengine.com/packages/build-in-container"
PLATFORM_PACKAGE_SUFFIXES = (".deb", ".rpm", ".msi")


@dataclass(frozen=True)
class PlannedFile:
    """A file to publish, and how it appears in the release metadata."""

    # The file to release, as built. In the build output, never modified.
    source: Path
    # The published copy in the release dir. .rpm and .deb copies are signed,
    # unless --no-sign. None for debug releases (nightlies): nothing is
    # copied, and the metadata links to the source on buildcache.
    destination: Path | None
    # Download link in the metadata. For releases, where destination ends up
    # on S3 once uploaded. For debug releases (nightlies), the source on
    # buildcache.
    url: str
    # Artifact section. "Policy Server" and "Hosts (Clients)" for enterprise
    # packages, "Binary packages" for community packages, and "Additional
    # Assets" for tarballs and the Vagrant quickstart.
    section: str
    # Shown on the downloads page, e.g. "Debian 12" or "Masterfiles source
    # tarball"
    title: str
    # e.g. "x86_64", "aarch64", or "no arch" for tarballs
    arch: str
    # Selects the package in self-upgrade policy, e.g.
    # "!am_policy_hub.debian_12.x86_64"
    classexpr: str
    # Build label the file came from, e.g. "PACKAGES_x86_64_linux_debian_12"
    package: str


def _section(project: str, hub: bool) -> str:
    if project == "community":
        return "Binary packages"
    return "Policy Server" if hub else "Hosts (Clients)"


def _release_path(project: str, version: str, hub: bool, release_dir: str) -> str:
    """Return the directory in the release, relative to its root."""
    if project == "community":
        return f"community_binaries/Community-{version}/{release_dir}"
    role = "hub" if hub else "agent"
    return f"enterprise/Enterprise-{version}/{role}/{release_dir}"


def plan_packages(
    project: str,
    version: str,
    build: BuildOutput,
    input_dir: str,
    output_dir: str,
    debug: bool,
) -> list[PlannedFile]:
    """Plan the platform packages, i.e. .deb, .rpm and .msi, of every label."""
    build_tag = Path(input_dir).resolve().name
    planned: list[PlannedFile] = []
    platforms = {label: get_platform(label, project) for label in build.labels}
    for label in sorted(platforms, key=lambda label: platforms[label].sort_key()):
        platform = platforms[label]
        label_dir = build.labels[label]
        release_path = _release_path(
            project, version, platform.hub, platform.release_dir
        )
        for source in label_dir.packages:
            if not source.name.endswith(PLATFORM_PACKAGE_SUFFIXES):
                continue
            if debug:
                destination = None
                url = f"{BUILDCACHE_URL}/{build_tag}/{label}/{source.name}"
            else:
                destination = Path(output_dir) / "release" / release_path / source.name
                url = f"{S3_URL}/{release_path}/{source.name}"
            planned.append(
                PlannedFile(
                    source,
                    destination,
                    url,
                    _section(project, platform.hub),
                    platform.title,
                    platform.arch,
                    platform.classexpr,
                    label,
                )
            )
    return planned
