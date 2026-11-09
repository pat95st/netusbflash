# Releasing

Installed devices update themselves from the GitHub releases of the
repository set under **Administration → Updates** (default
`pat95st/netusbflash`). A release is made by pushing a tag; the workflow
`.github/workflows/release.yml` does the rest.

## Steps

1. Update `VERSION` (for example `0.2.0` or `0.2.0-beta.1`).
2. Move the entries under *Unreleased* in `CHANGELOG.md` to a new section
   `## <version> – <date>`. This section becomes the release notes.
3. Commit, then tag and push:

   ```bash
   git tag v0.2.0
   git push origin main v0.2.0
   ```

The workflow

- fails if `VERSION` does not match the tag,
- runs the Python tests, `php -l` and the translation check,
- downloads FileGator and builds `netusbflash-<version>.tar.gz`
  (the `git archive` of the tag plus `vendor/filegator`) and a `.sha256` file,
- publishes the release. Tags with a hyphen (`v0.2.0-rc.1`) become
  pre-releases.

## What a device does

1. **Check** (daily if enabled, or by hand): reads
   `https://api.github.com/repos/<repo>/releases` and picks the newest version
   by semantic versioning. Pre-releases count only if they are enabled.
2. **Install**: downloads the archive (falls back to GitHub's source tarball
   when the asset is missing), compares the SHA-256 checksum, unpacks it
   without links or paths outside the work folder, checks that the archive's
   `VERSION` is the expected one, then runs `packaging/install.sh --upgrade`
   in a transient systemd unit (`netusbflash-software-update-<time>`).
   Output goes to `/var/lib/netusbflash/updates/update.log`.

Settings, users, targets and the USB image are kept. The service restarts,
so the stick is briefly disconnected from the host.

Operating system updates (`apt-get update && apt-get full-upgrade`) run the
same way in `netusbflash-os-update-<time>`.

## Testing a release candidate

Publish a pre-release tag (`v0.2.0-rc.1`) and enable *Include pre-releases*
on a test device.
