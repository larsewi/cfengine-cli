#!/usr/bin/env bash
# End-to-end test of cfengine dev release and update-repo, with real tools.
#
# Recreates the published community and enterprise 3.29.0 releases from fake
# packages, and compares the release data with the published one. Needs gpg,
# rpm, rpmbuild, rpmsign, debsigs, apt-ftparchive and createrepo_c, so CI runs
# it as its own job. Run from the repo root, with cfengine in PATH, e.g. via
# uv run.

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

gpg --armor --export contact@northern.tech >"$WORK/key.asc"
rpm --dbpath "$WORK/rpmdb" --import "$WORK/key.asc"

# An output dir with releases.json as before the release
new_output() {
    local project="$1" output="$2"
    mkdir -p "$output/release-data/$project"
    python3 - "$DATA/$project-releases.json" "$VERSION" \
        >"$output/release-data/$project/releases.json" <<'EOF'
import json, sys
data = json.load(open(sys.argv[1]))
data["releases"] = [r for r in data["releases"] if r["version"] != sys.argv[2]]
print(json.dumps(data))
EOF
}

release() {
    local project="$1"
    shift
    cfengine dev release --project "$project" --version "$VERSION" \
        --input "$WORK/build-$project" --output "$@"
}

update_repo() {
    cfengine dev update-repo --version "$VERSION" \
        --input "$WORK/build-community" --output "$1"
}

test_release() {
    local project="$1"
    local out="$WORK/out-$project"

    echo "== $project $VERSION"
    echo "Generating the build output"
    python3 "$TESTS/make_build.py" "$DATA/$project-$VERSION.json" \
        "$WORK/probe.deb" "$RPM" "$WORK/build-$project"

    new_output "$project" "$out"
    release "$project" "$out"
    if [ "$project" = community ]; then
        update_repo "$out"
    fi

    echo "Comparing the release data with the published one"
    python3 "$TESTS/compare.py" "$DATA/$project-$VERSION.json" \
        "$out/release-data/$project/$VERSION.json" "$VERSION"
    python3 "$TESTS/compare.py" "$DATA/$project-releases.json" \
        "$out/release-data/$project/releases.json" "$VERSION"

    echo "Verifying the package signatures"
    find "$out/release" -name '*.rpm' | while read -r rpm; do
        rpm --dbpath "$WORK/rpmdb" -K "$rpm" | grep -q "signatures OK"
    done
    find "$out/release" -name '*.deb' | while read -r deb; do
        debsigs --verify "$deb" >/dev/null
    done

    echo "Checking that no temporary files are left"
    if find "$out" -maxdepth 1 -name '.tmp-*' | grep -q .; then
        echo "Temporary files left in $out" >&2
        exit 1
    fi

    echo "Checking that signing is reproducible"
    new_output "$project" "$WORK/again-$project"
    release "$project" "$WORK/again-$project" >/dev/null
    diff -r "$out/release" "$WORK/again-$project/release"
}

test_repo() {
    local out="$WORK/out-community"

    echo "== community repositories"
    echo "Verifying the repository signatures"
    find "$out/repo" -name '*.rpm' | while read -r rpm; do
        rpm --dbpath "$WORK/rpmdb" -K "$rpm" | grep -q "signatures OK"
    done
    local stable="$out/repo/apt/packages/dists/stable"
    gpg --verify "$stable/Release.gpg" "$stable/Release" 2>/dev/null
    gpg --verify "$stable/InRelease" 2>/dev/null
    for repomd in "$out"/repo/yum/*/repodata/repomd.xml; do
        gpg --verify "$repomd.asc" "$repomd" 2>/dev/null
    done

    echo "Checking that update-repo refuses unsigned rpms"
    new_output community "$WORK/unsigned"
    release community "$WORK/unsigned" --no-sign >/dev/null
    if update_repo "$WORK/unsigned" >"$WORK/unsigned.log" 2>&1; then
        echo "update-repo accepted unsigned rpms" >&2
        exit 1
    fi
    grep -q "Not signed" "$WORK/unsigned.log"
}

test_release community
test_repo
test_release enterprise

echo "All release end-to-end tests passed"
