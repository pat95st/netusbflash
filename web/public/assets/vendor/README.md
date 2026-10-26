# Third-party front-end files

The web UI uses [Bootstrap](https://getbootstrap.com/) 5 and
[Bootstrap Icons](https://icons.getbootstrap.com/), both MIT licensed. They are
served from the Pi itself; no CDN is used. The files are part of the
repository, so a Pi needs no internet access to show the UI.

To update them, change the versions in `packaging/fetch-vendor.sh` and run:

```bash
./packaging/fetch-vendor.sh --force
```

The script downloads the official release archives from GitHub, copies only
the files the UI needs and writes `VERSIONS` and `SHA256SUMS`.
