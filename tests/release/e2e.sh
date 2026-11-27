#!/usr/bin/env bash
# End-to-end test of cfengine dev release and update-repo, with real tools.
#
# Recreates the published community 3.29.0 release from fake packages, and
# compares the release data with the published one. Needs gpg, rpm, rpmbuild,
# rpmsign, debsigs, apt-ftparchive and createrepo_c, so CI runs it as its own
# job. Run from the repo root, with cfengine in PATH, e.g. via uv run.

set -euo pipefail

TESTS="$(pwd)/tests/release"
DATA="$TESTS/data"
VERSION=3.29.0
# The build time of the packages, as build-in-container sets it
export SOURCE_DATE_EPOCH=1700000000

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# A test key, so a real keyring is never used. Created before the build time,
# as gpg refuses to make signatures older than the key.
export GNUPGHOME="$WORK/gnupg"
mkdir -m 700 "$GNUPGHOME"
gpg --batch --quiet --faked-system-time 1600000000 --passphrase '' \
    --quick-gen-key "Test <contact@northern.tech>" rsa3072 sign never

echo "Building a small .deb and .rpm"
mkdir -p "$WORK/deb/DEBIAN" "$WORK/rpm/SPECS"
cat >"$WORK/deb/DEBIAN/control" <<'EOF'
Package: probe
Version: 1.0
Architecture: all
Maintainer: Test <test@example.invalid>
Description: Test package
EOF
dpkg-deb --root-owner-group --build "$WORK/deb" "$WORK/probe.deb" >/dev/null
cat >"$WORK/rpm/SPECS/probe.spec" <<'EOF'
Name: probe
Version: 1.0
Release: 1
Summary: Test package
License: MIT
BuildArch: noarch
%description
Test package
%files
EOF
# Its own rpm database, also used to verify signatures below. Debian hosts
# have no system one.
rpm --dbpath "$WORK/rpmdb" --initdb
rpmbuild --quiet -bb --define "_topdir $WORK/rpm" --define "_dbpath $WORK/rpmdb" \
    --define "use_source_date_epoch_as_buildtime 1" "$WORK/rpm/SPECS/probe.spec"
RPM="$WORK/rpm/RPMS/noarch/probe-1.0-1.noarch.rpm"

echo "Generating the build output of community $VERSION"
python3 "$TESTS/make_build.py" "$DATA/community-$VERSION.json" \
    "$WORK/probe.deb" "$RPM" "$WORK/build"

# An output dir with releases.json as before the release
new_output() {
    mkdir -p "$1/release-data/community"
    python3 - "$DATA/community-releases.json" "$VERSION" \
        >"$1/release-data/community/releases.json" <<'EOF'
import json, sys
data = json.load(open(sys.argv[1]))
data["releases"] = [r for r in data["releases"] if r["version"] != sys.argv[2]]
print(json.dumps(data))
EOF
}

release() {
    cfengine dev release --project community --version "$VERSION" \
        --input "$WORK/build" --output "$@"
}

update_repo() {
    cfengine dev update-repo --version "$VERSION" --input "$WORK/build" --output "$1"
}

OUT="$WORK/out"
new_output "$OUT"
release "$OUT"
update_repo "$OUT"

echo "Comparing the release data with the published one"
python3 "$TESTS/compare.py" "$DATA/community-$VERSION.json" \
    "$OUT/release-data/community/$VERSION.json" "$VERSION"
python3 "$TESTS/compare.py" "$DATA/community-releases.json" \
    "$OUT/release-data/community/releases.json" "$VERSION"

echo "Verifying the signatures"
gpg --armor --export contact@northern.tech >"$WORK/key.asc"
rpm --dbpath "$WORK/rpmdb" --import "$WORK/key.asc"
find "$OUT/release" "$OUT/repo" -name '*.rpm' | while read -r rpm; do
    rpm --dbpath "$WORK/rpmdb" -K "$rpm" | grep -q "signatures OK"
done
find "$OUT/release" -name '*.deb' | while read -r deb; do
    debsigs --verify "$deb" >/dev/null
done
STABLE="$OUT/repo/apt/packages/dists/stable"
gpg --verify "$STABLE/Release.gpg" "$STABLE/Release" 2>/dev/null
gpg --verify "$STABLE/InRelease" 2>/dev/null
for repomd in "$OUT"/repo/yum/*/repodata/repomd.xml; do
    gpg --verify "$repomd.asc" "$repomd" 2>/dev/null
done

echo "Checking that no temporary files are left"
if find "$OUT" -maxdepth 1 -name '.tmp-*' | grep -q .; then
    echo "Temporary files left in $OUT" >&2
    exit 1
fi

echo "Checking that signing is reproducible"
new_output "$WORK/again"
release "$WORK/again" >/dev/null
diff -r "$OUT/release" "$WORK/again/release"

echo "Checking that update-repo refuses unsigned rpms"
new_output "$WORK/unsigned"
release "$WORK/unsigned" --no-sign >/dev/null
if update_repo "$WORK/unsigned" >"$WORK/unsigned.log" 2>&1; then
    echo "update-repo accepted unsigned rpms" >&2
    exit 1
fi
grep -q "Not signed" "$WORK/unsigned.log"

echo "All release end-to-end tests passed"
