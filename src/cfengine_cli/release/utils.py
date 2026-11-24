import shutil
import subprocess
from pathlib import Path

from cfengine_cli.utils import UserError

SIGNED_SUFFIXES = (".rpm", ".deb")
SIGNING_TOOLS = ("rpm", "rpmsign", "debsigs")
AR_MAGIC = b"!<arch>\n"


def run(command: list[str]) -> str:
    """Run a command and return its stdout. stderr goes to the terminal."""
    try:
        return subprocess.run(
            command, check=True, stdout=subprocess.PIPE, text=True
        ).stdout
    except subprocess.CalledProcessError as e:
        # A UserError, as a failed command is not a bug in cfengine-cli
        raise UserError(f"Command failed: {' '.join(command)}") from e


def _deb_build_time(path: Path) -> int:
    """Return the mtime of the first ar member, set from SOURCE_DATE_EPOCH."""
    with open(path, "rb") as f:
        header = f.read(len(AR_MAGIC) + 60)
    if not header.startswith(AR_MAGIC) or len(header) < len(AR_MAGIC) + 60:
        raise UserError(f"Not a .deb: '{path}'")
    # An ar member header starts with a 16 byte name, then a 12 byte mtime
    mtime = header[len(AR_MAGIC) + 16 : len(AR_MAGIC) + 28]
    return int(mtime.decode("ascii"))


def _rpm_build_time(path: Path) -> int:
    """Return BUILDTIME, set from SOURCE_DATE_EPOCH by build-in-container."""
    # Skip signature checking. The package is not signed yet, and checking
    # needs the rpm database, which Debian hosts lack.
    return int(run(["rpm", "-qp", "--nosignature", "--qf", "%{BUILDTIME}", str(path)]))


def build_time(path: Path) -> int:
    """Return the package's SOURCE_DATE_EPOCH."""
    if path.name.endswith(".rpm"):
        return _rpm_build_time(path)
    return _deb_build_time(path)


def sign(path: Path, time: int) -> None:
    """Sign a .rpm or .deb with the given signature creation time.

    A fixed time makes the signed package reproducible with the same key.
    """
    # The "!" stops the faked clock, so the time does not tick during signing
    faked_time = f"--faked-system-time {time}!"
    if path.name.endswith(".rpm"):
        _ = run(
            [
                "rpmsign",
                "--resign",
                "--digest-algo=sha256",
                "--define",
                f"_gpg_sign_cmd_extra_args {faked_time}",
                str(path),
            ]
        )
    else:
        _ = run(["debsigs", "--sign=origin", f"--gpgopts={faked_time}", str(path)])
        # debsigs can print an error, yet exit 0 with an unsigned package.
        # So check that the signature is there and good.
        _ = run(["debsigs", "--verify", str(path)])


def check_signing_tools() -> None:
    missing = [tool for tool in SIGNING_TOOLS if shutil.which(tool) is None]
    if missing:
        raise UserError(f"Signing tools not found: {', '.join(missing)}")


def copy_file(source: Path, destination: Path, signed: bool) -> None:
    """Copy source to destination, and sign the copy if signed.

    Done under a temporary name, so a file at the destination is always
    complete and signed.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".tmp-{destination.name}")
    try:
        _ = shutil.copyfile(source, temporary)
        if signed:
            sign(temporary, build_time(source))
        _ = temporary.rename(destination)
    except BaseException:
        # Also on Ctrl-C. Only SIGKILL or a crash leaves it behind.
        temporary.unlink(missing_ok=True)
        raise
