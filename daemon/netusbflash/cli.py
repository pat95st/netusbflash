"""Command-line tool for recovery tasks (run as root on the Pi).

Examples:
    netusbflash-cli setup show-code
    netusbflash-cli setup reset [--wipe-users]
    netusbflash-cli user list
    netusbflash-cli user reset-password <username>
    netusbflash-cli user unlock <username>
    netusbflash-cli usb teardown
"""

from __future__ import annotations

import argparse
import sys

from .auth import AuthService, generate_password
from .config import load_paths
from .db import Database
from .setup import SetupState


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="netusbflash-cli")
    sub = parser.add_subparsers(dest="area", required=True)

    setup = sub.add_parser("setup", help="setup wizard")
    setup_sub = setup.add_subparsers(dest="action", required=True)
    setup_sub.add_parser("show-code", help="print the one-time setup code")
    reset = setup_sub.add_parser("reset", help="run the setup wizard again")
    reset.add_argument("--wipe-users", action="store_true", help="also delete all web users")

    user = sub.add_parser("user", help="web interface users")
    user_sub = user.add_subparsers(dest="action", required=True)
    user_sub.add_parser("list")
    rp = user_sub.add_parser("reset-password")
    rp.add_argument("username")
    ul = user_sub.add_parser("unlock")
    ul.add_argument("username")

    usb = sub.add_parser("usb", help="USB gadget")
    usb_sub = usb.add_subparsers(dest="action", required=True)
    usb_sub.add_parser("teardown", help="disconnect and remove the USB gadget")

    args = parser.parse_args(argv)
    paths = load_paths()
    paths.ensure()
    db = Database(paths.db)
    db.migrate()
    auth = AuthService(db)
    state = SetupState(db, paths)

    if args.area == "setup":
        if args.action == "show-code":
            if state.completed():
                print("Setup is already completed. Use 'netusbflash-cli setup reset' to run it again.")
                return 1
            state.ensure_code()
            print(state.read_code())
            return 0
        state.reset(wipe_users=args.wipe_users)
        print("Setup wizard reset. New setup code:", state.read_code())
        return 0

    if args.area == "usb":
        from .gadget import ConfigfsGadget
        ConfigfsGadget(paths).teardown()
        print("USB gadget removed.")
        return 0

    if args.action == "list":
        for row in db.all("SELECT username, role, email, disabled FROM users ORDER BY username"):
            flag = " (disabled)" if row["disabled"] else ""
            print(f"{row['username']:<24} {row['role']:<10} {row['email']}{flag}")
        return 0

    found = auth.find_user(args.username)
    if found is None:
        print(f"No such user: {args.username}", file=sys.stderr)
        return 1
    if args.action == "unlock":
        db.run("UPDATE users SET failed_logins = 0, locked_until = 0, disabled = 0 WHERE id = ?", (found["id"],))
        print(f"Unlocked {found['username']}")
        return 0
    password = generate_password()
    auth.set_password(found["id"], password, must_change=True)
    db.audit(None, "cli.reset_password", found["username"])
    print(f"Temporary password for {found['username']}: {password}")
    print("The user must change it at the next login.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
