import re


def version_key(version: str) -> tuple[int, ...]:
    """Sort key for versions in releases.json.

    master > 3.30.x > 3.30.0 > 3.27.0 > 3.15.0 > 3.15.0b1. We no longer
    release betas, but releases.json still has old ones like 3.15.0b1.
    """
    if version == "master":
        return (999,)
    match = re.fullmatch(r"(\d+(?:\.\d+)*)(.*)", version)
    if not match:
        return (0,)
    parts = [int(x) for x in match.group(1).split(".")]
    remainder = match.group(2)
    if remainder == ".x":
        # A branch nightly sorts above every release on its branch
        parts.append(999)
        suffix = (2, 0)
    elif remainder == "":
        suffix = (2, 0)
    elif remainder.startswith("b"):
        suffix = (1, int(remainder[1:]))
    elif remainder.startswith("a"):
        suffix = (0, int(remainder[1:]))
    else:
        suffix = (0, 0)
    return tuple(parts) + suffix


def _minor(version: str) -> int:
    """Return the minor version, e.g. 30 for 3.30.0, or 0 for master."""
    match = re.match(r"\d+\.(\d+)", version)
    return int(match.group(1)) if match else 0


def is_lts(version: str) -> bool:
    """Return True if the version is on an LTS branch, e.g. 3.27.x or 3.30.x."""
    minor = _minor(version)
    if minor < 11:
        return minor % 3 == 1  # 3.7, 3.10
    return minor % 3 == 0  # 3.12, 3.15, ...


def support_end(version: str) -> tuple[str, str]:
    """Return when the version's branch goes out of support.

    E.g. ("2028-12", "December 2028") for 3.27.x.
    """
    # Same formula as the legacy release.py in the infra repo. LTS branches
    # come 1.5 years apart, so their support ends alternate between December
    # of one year and August of the next. The value below is a year as a
    # decimal number. (minor + 1) / 2 is a whole number or ends in .5, so
    # adding 2014.4 makes it end in .4 or .9. Rounding then gives the year:
    # .4 rounds down and means December, .9 rounds up and means August.
    # E.g. 3.27: 2028.4 -> December 2028, 3.30: 2029.9 -> August 2030.
    minor = _minor(version)
    if minor < 11:
        value = minor / 2 + 2014.4
    else:
        value = (minor + 1) / 2 + 2014.4
    year = round(value)
    if value - year > 0.2:
        return f"{year}-12", f"December {year}"
    return f"{year}-08", f"August {year}"


def version_title(project: str, version: str) -> str:
    """Return the title shown for a version.

    E.g. "3.27.0 LTS (supported until December 2028)" for enterprise.
    """
    enterprise = project == "enterprise"
    if is_lts(version):
        title = f"{version} LTS"
        if enterprise:
            _, until = support_end(version)
            title += f" (supported until {until})"
        return title
    title = f"{version} non-LTS"
    if enterprise:
        title += " (unsupported)"
    return title
