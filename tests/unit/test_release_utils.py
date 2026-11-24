from pathlib import Path

import pytest

from cfengine_cli.release.utils import build_time, run
from cfengine_cli.utils import UserError


def test_build_time_not_a_deb(tmp_path: Path) -> None:
    deb = tmp_path / "cfengine-nova_3.30.0-1_amd64.deb"
    _ = deb.write_text("not an ar archive")
    with pytest.raises(UserError, match="Not a .deb"):
        _ = build_time(deb)


def test_run() -> None:
    assert run(["sh", "-c", "echo out; echo warning >&2"]) == "out\n"


def test_run_fails_on_exit_status() -> None:
    with pytest.raises(UserError, match="Command failed: sh -c exit 1"):
        _ = run(["sh", "-c", "exit 1"])
