from pathlib import Path

from cfengine_cli.release.build_output import BuildOutput, OutputDir
from cfengine_cli.release.plan import PlannedFile, plan_packages

INPUT = Path("/builds/jenkins-master-nightly-pipeline-123")
OUTPUT = "/var/www/buildcache"
HUB = "PACKAGES_HUB_x86_64_linux_debian_12"
AGENT = "PACKAGES_x86_64_linux_redhat_9"
WINDOWS = "PACKAGES_x86_64_mingw"
S3 = "https://cfengine-package-repos.s3.amazonaws.com"

# Files in each label dir. Only .deb, .rpm and .msi are platform packages.
FILES = {
    HUB: [
        "cfengine-nova-hub-3.30.0-1.x86_64.pkg.tar.gz",
        "cfengine-nova-hub_3.30.0-1_amd64.deb",
    ],
    AGENT: ["cfengine-nova-3.30.0-1.el9.x86_64.rpm"],
    WINDOWS: ["cfengine-nova-3.30.0-1-x86_64.msi"],
}


def _output_dir(label: str, names: list[str]) -> OutputDir:
    return OutputDir(
        [INPUT / label / name for name in names], INPUT / label / "sha256sums.txt"
    )


def _build(*labels: str) -> BuildOutput:
    """A build output with the given labels. No files need to exist."""
    return BuildOutput(
        {label: _output_dir(label, FILES[label]) for label in labels},
        _output_dir("tarballs", ["cfengine-3.30.0.tar.gz"]),
        None,
    )


def test_plan_packages_enterprise() -> None:
    planned = plan_packages(
        "enterprise", "3.30.0", _build(HUB, AGENT), str(INPUT), OUTPUT, False
    )
    hub_deb = "cfengine-nova-hub_3.30.0-1_amd64.deb"
    hub_path = "enterprise/Enterprise-3.30.0/hub/debian_12_x86_64"
    agent_rpm = "cfengine-nova-3.30.0-1.el9.x86_64.rpm"
    agent_path = "enterprise/Enterprise-3.30.0/agent/agent_rhel9_x86_64"
    # The hub's .pkg.tar.gz is not a platform package, so it is skipped
    assert planned == [
        PlannedFile(
            INPUT / HUB / hub_deb,
            Path(OUTPUT) / "release" / hub_path / hub_deb,
            f"{S3}/{hub_path}/{hub_deb}",
            "Policy Server",
            "Debian 12",
            "x86_64",
            "am_policy_hub.debian_12.x86_64",
            HUB,
        ),
        PlannedFile(
            INPUT / AGENT / agent_rpm,
            Path(OUTPUT) / "release" / agent_path / agent_rpm,
            f"{S3}/{agent_path}/{agent_rpm}",
            "Hosts (Clients)",
            "Red Hat / CentOS 9",
            "x86_64",
            "!am_policy_hub.(redhat_9|centos_9).x86_64",
            AGENT,
        ),
    ]


def test_plan_packages_community() -> None:
    [planned] = plan_packages(
        "community", "3.30.0", _build(AGENT), str(INPUT), OUTPUT, False
    )
    rpm = "cfengine-nova-3.30.0-1.el9.x86_64.rpm"
    path = "community_binaries/Community-3.30.0/agent_rhel9_x86_64"
    assert planned.destination == Path(OUTPUT) / "release" / path / rpm
    assert planned.url == f"{S3}/{path}/{rpm}"
    assert planned.section == "Binary packages"
    assert planned.classexpr == "(redhat_9|centos_9).x86_64"


def test_plan_packages_debug() -> None:
    [planned] = plan_packages(
        "enterprise", "master", _build(AGENT), str(INPUT), OUTPUT, True
    )
    assert planned.destination is None
    assert planned.url == (
        "http://buildcache.cfengine.com/packages/build-in-container/"
        f"jenkins-master-nightly-pipeline-123/{AGENT}/"
        "cfengine-nova-3.30.0-1.el9.x86_64.rpm"
    )


def test_plan_packages_windows() -> None:
    [planned] = plan_packages(
        "enterprise", "3.30.0", _build(WINDOWS), str(INPUT), OUTPUT, False
    )
    assert planned.source.name == "cfengine-nova-3.30.0-1-x86_64.msi"
    assert planned.url == (
        f"{S3}/enterprise/Enterprise-3.30.0/agent/windows_x86_64/"
        "cfengine-nova-3.30.0-1-x86_64.msi"
    )
