import pytest

from cfengine_cli.release.metadata import (
    is_lts,
    support_end,
    version_key,
    version_title,
)

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


@pytest.mark.parametrize(
    "version", ["3.7.0", "3.10.0", "3.12.0", "3.24.3", "3.27.0", "3.30.0", "3.30.x"]
)
def test_is_lts(version: str) -> None:
    assert is_lts(version)


@pytest.mark.parametrize(
    "version", ["3.8.0", "3.11.0", "3.26.0", "3.28.0", "3.29.0", "3.31.0", "master"]
)
def test_is_not_lts(version: str) -> None:
    assert not is_lts(version)


# supported_until of each LTS branch in the published enterprise releases.json,
# plus 3.30.x
@pytest.mark.parametrize(
    "version, date",
    [
        ("3.7.x", "2018-08"),
        ("3.10.x", "2019-12"),
        ("3.12.x", "2021-08"),
        ("3.15.x", "2022-12"),
        ("3.18.x", "2024-08"),
        ("3.21.x", "2025-12"),
        ("3.24.x", "2027-08"),
        ("3.27.x", "2028-12"),
        ("3.30.x", "2030-08"),
    ],
)
def test_support_end_date(version: str, date: str) -> None:
    assert support_end(version)[0] == date


def test_support_end_text() -> None:
    assert support_end("3.27.0") == ("2028-12", "December 2028")
    assert support_end("3.30.0") == ("2030-08", "August 2030")


# The first 8 are from the published release-data/<project>/<version>.json
@pytest.mark.parametrize(
    "project, version, title",
    [
        ("enterprise", "master", "master non-LTS (unsupported)"),
        ("enterprise", "3.27.x", "3.27.x LTS (supported until December 2028)"),
        ("enterprise", "3.27.0", "3.27.0 LTS (supported until December 2028)"),
        ("enterprise", "3.26.0", "3.26.0 non-LTS (unsupported)"),
        ("community", "master", "master non-LTS"),
        ("community", "3.27.x", "3.27.x LTS"),
        ("community", "3.27.0", "3.27.0 LTS"),
        ("community", "3.26.0", "3.26.0 non-LTS"),
        ("enterprise", "3.30.0", "3.30.0 LTS (supported until August 2030)"),
        ("enterprise", "3.31.0", "3.31.0 non-LTS (unsupported)"),
    ],
)
def test_version_title(project: str, version: str, title: str) -> None:
    assert version_title(project, version) == title
