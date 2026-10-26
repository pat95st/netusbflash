# Third-party front-end files

The web UI uses [Bootstrap](https://getbootstrap.com/) 5 and
[Bootstrap Icons](https://icons.getbootstrap.com/), both MIT licensed. They are
served from the Pi itself; no CDN is used.

Populate this folder with:

```bash
./packaging/fetch-vendor.sh
```

The script pins the versions, copies only the files the UI needs (including the
license files) and writes `VERSIONS` and `SHA256SUMS`. Commit the result so a
Pi can be installed without downloading anything from npm.
