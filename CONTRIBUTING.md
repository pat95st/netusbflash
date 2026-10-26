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
./scripts/dev-server.sh          # simulated USB stick, UI on http://127.0.0.1:8080
```

## Checks before a pull request

```bash
cd daemon && python3 -m unittest discover -s tests
php web/tests/check_lang.php
find web -name '*.php' -exec php -l {} \; | grep -v 'No syntax errors'
bash -n packaging/install.sh
```

## Code style

- Python: PEP 8, type hints, standard library first. External commands only via
  `system.run()` with an argument list, never a shell string.
- PHP: `declare(strict_types=1)`, PSR-12 style, escape all output with `e()`, every form
  posts a CSRF token (`csrf_field()`), no inline JavaScript or CSS (the CSP blocks it).
- The web interface never changes the system directly; add an API endpoint instead and
  check the role there.
