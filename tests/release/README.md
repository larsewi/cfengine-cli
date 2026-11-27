# Release end-to-end test

`e2e.sh` tests `cfengine dev release` and `cfengine dev update-repo` with the
real packaging and signing tools. It recreates a published release from small
fake packages and compares the release data with the published one. CI runs it
as its own job, see `.github/workflows/make-check.yml`.

```bash
uv run bash tests/release/e2e.sh
```

It needs gpg, rpm, rpmbuild, rpmsign, debsigs, apt-ftparchive and
createrepo_c. It uses its own gpg key, never a real keyring.

## Data

The files in `data/` are release data from
`https://cfengine-package-repos.s3.amazonaws.com/release-data/community/`:
`community-3.29.0.json` and `community-releases.json`. They are excluded from
prettier, to keep the published format.
