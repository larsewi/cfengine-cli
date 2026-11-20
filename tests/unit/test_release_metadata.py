from cfengine_cli.release.metadata import version_key

# Every version in the published enterprise releases.json, highest first
EXPECTED = [
    "master", "3.27.x", "3.27.0", "3.26.0", "3.25.0", "3.24.x",
    "3.24.3", "3.24.2", "3.24.1", "3.24.0", "3.23.0", "3.22.0",
    "3.21.x", "3.21.8", "3.21.7", "3.21.6", "3.21.5", "3.21.4",
    "3.21.3", "3.21.2", "3.21.1", "3.21.0", "3.20.0", "3.19.0",
    "3.18.x", "3.18.8", "3.18.7", "3.18.6", "3.18.5", "3.18.4",
    "3.18.3", "3.18.2", "3.18.1", "3.18.0", "3.17.0", "3.16.0",
    "3.15.x", "3.15.7", "3.15.6", "3.15.5", "3.15.4", "3.15.3",
    "3.15.2", "3.15.1", "3.15.0", "3.15.0b1", "3.14.0", "3.13.0",
    "3.12.x", "3.12.7", "3.12.6", "3.12.5", "3.12.4", "3.12.3",
    "3.12.2", "3.12.1", "3.12.0", "3.11.0", "3.11.0b1", "3.10.x",
    "3.10.7", "3.10.6", "3.10.5", "3.10.4", "3.10.3", "3.10.2",
    "3.10.1", "3.10.0", "3.9.2", "3.9.0", "3.9.0b1", "3.8.2",
    "3.8.1", "3.8.0", "3.8.0b1", "3.7.8", "3.7.7", "3.7.6",
    "3.7.5", "3.7.4", "3.7.3", "3.7.2", "3.7.1", "3.7.0",
    "3.6.7", "3.6.6", "3.6.5", "3.6.4", "3.6.3", "3.6.2",
    "3.6.1", "3.6.0",
]  # fmt: skip


def test_version_key_stable_releases() -> None:
    assert version_key("3.24.0") > version_key("3.9.2")
    assert version_key("3.10.0") > version_key("3.9.2")
    assert version_key("3.27.0") > version_key("3.24.3")


def test_version_key_pre_releases() -> None:
    assert version_key("3.15.0") > version_key("3.15.0b1")
    assert version_key("3.15.0b1") > version_key("3.15.0a1")
    assert version_key("3.15.0b1") > version_key("3.15.0a2")
    assert version_key("3.15.0b2") > version_key("3.15.0b1")


def test_version_key_branch_nightlies() -> None:
    assert version_key("3.27.x") > version_key("3.27.0")
    assert version_key("3.27.x") > version_key("3.24.x")
    assert version_key("3.30.0") > version_key("3.27.x")


def test_version_key_master() -> None:
    assert version_key("master") > version_key("3.30.x")


def test_version_key_unknown() -> None:
    assert version_key("unknown") < version_key("3.6.0")


def test_version_key_sort_order() -> None:
    # Sorting as strings scrambles the order, e.g. 3.10.0 before 3.9.2
    assert sorted(sorted(EXPECTED), key=version_key, reverse=True) == EXPECTED
