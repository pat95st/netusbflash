# Contributing

## Language

- Source code, comments, log messages, API, documentation and commit messages are in **English**.
- The web interface is in **English and German**. Every text lives in `web/lang/en.php` and
  `web/lang/de.php`; add each new key to both files. Never hard-code UI text in templates.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(mailer): add digest mode
fix(gadget): reattach the stick when a sync fails
docs(setup): explain the USB-C power splitter
test(api): cover the last-admin guard
```

Common types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `build`.
Scopes follow the module names (`gadget`, `monitor`, `uploader`, `mailer`, `api`, `auth`, `web`, `install`, …).

## Development setup

```bash
./packaging/fetch-filegator.sh   # once: file manager into vendor/filegator (git-ignored)
./scripts/dev-server.sh          # simulated USB stick, UI on http://127.0.0.1:8080
```

Third-party front-end files (Bootstrap, Bootstrap Icons, Quill) are committed in
`web/public/assets/vendor`; update them with `packaging/fetch-vendor.sh`.
Releases are described in [docs/releasing.md](docs/releasing.md).

## Checks before a pull request

```bash
cd daemon && python3 -m unittest discover -s tests
php web/tests/check_lang.php
node web/tests/e2e.js            # browser test, needs a fresh ./scripts/dev-server.sh on port 8099
find web -name '*.php' -exec php -l {} \; | grep -v 'No syntax errors'
bash -n packaging/install.sh
```

## Code style

- Python: PEP 8, type hints, standard library first. External commands only via
  `system.run()` with an argument list, never a shell string.
- PHP: `declare(strict_types=1)`, PSR-12 style, escape all output with `e()`, every form
  posts a CSRF token (`csrf_field()`), no inline JavaScript or CSS (the CSP blocks it; only
  the notifications page allows inline styles for the mail editor).
- The web interface never changes the system directly; add an API endpoint instead and
  check the role there.
