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
