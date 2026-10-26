"""Local JSON API served over a Unix socket.

Only the web UI (PHP-FPM as www-data, member of group "netusbflash") can
reach the socket. Every request after login carries a session token in the
X-Session-Token header; roles are checked here, never only in the UI.
"""

from __future__ import annotations

import grp
import json
import logging
import os
import re
import socketserver
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable
from urllib.parse import parse_qs, urlsplit

from .auth import ROLES, has_role
from .config import SOCKET_GROUP
from .validate import ValidationError

if TYPE_CHECKING:
    from .service import Context

log = logging.getLogger(__name__)

MAX_BODY = 1024 * 1024


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str = "", fields: dict[str, str] | None = None):
        super().__init__(message or code)
        self.status = status
        self.code = code
        self.message = message or code
        self.fields = fields or {}


class Request:
    def __init__(self, ctx: "Context", method: str, path: str, query: dict[str, list[str]],
                 headers: Any, body: dict[str, Any]):
        self.ctx = ctx
        self.method = method
        self.path = path
        self.query = query
        self.headers = headers
        self.body = body
        self.params: dict[str, str] = {}
        self.user: dict[str, Any] | None = None
        self.token: str | None = headers.get("X-Session-Token")

    def q(self, name: str, default: str = "") -> str:
        values = self.query.get(name)
        return values[0] if values else default

    def int_param(self, name: str) -> int:
        try:
            return int(self.params[name])
        except (KeyError, ValueError) as exc:
            raise ApiError(404, "not_found") from exc


Handler = Callable[[Request], Any]


class Router:
    def __init__(self) -> None:
        self.routes: list[tuple[str, re.Pattern[str], Handler, str]] = []

    def add(self, method: str, pattern: str, handler: Handler, access: str) -> None:
        """access: 'public', 'setup' (needs setup code) or a role name."""
        if access not in ("public", "setup") and access not in ROLES:
            raise ValueError(access)
        regex = re.compile("^/api/v1" + re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", pattern) + "$")
        self.routes.append((method, regex, handler, access))

    def match(self, method: str, path: str) -> tuple[Handler, str, dict[str, str]]:
        path_matched = False
        for route_method, regex, handler, access in self.routes:
            m = regex.match(path)
            if not m:
                continue
            path_matched = True
            if route_method == method:
                return handler, access, m.groupdict()
        if path_matched:
            raise ApiError(405, "method_not_allowed")
        raise ApiError(404, "not_found")


def dispatch(ctx: "Context", router: Router, req: Request) -> tuple[int, Any]:
    handler, access, params = router.match(req.method, req.path)
    req.params = params
    setup_done = ctx.setup.completed()
    if access == "setup":
        if setup_done:
            raise ApiError(409, "setup_done")
        if not ctx.setup.check(req.headers.get("X-Setup-Code")):
            raise ApiError(403, "setup_code_invalid")
    elif access != "public":
        if not setup_done:
            raise ApiError(409, "setup_required")
        req.user = ctx.auth.session_user(req.token)
        if req.user is None:
            raise ApiError(401, "session_expired")
        if not has_role(req.user, access):
            raise ApiError(403, "forbidden")
        if req.user["must_change_pw"] and not req.path.startswith("/api/v1/me"):
            if req.path not in ("/api/v1/auth/logout", "/api/v1/status"):
                raise ApiError(403, "password_change_required")
    result = handler(req)
    if isinstance(result, tuple):
        return result
    return 200, result if result is not None else {"ok": True}


class _ThreadingUnixServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True
    allow_reuse_address = True


def make_server(ctx: "Context", router: Router, socket_path: Path) -> socketserver.BaseServer:
    class RequestHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "netusbflash"

        def address_string(self) -> str:  # Unix sockets have no peer address
            return "local"

        def log_message(self, fmt: str, *args: Any) -> None:
            log.debug("api: " + fmt, *args)

        def _handle(self, method: str) -> None:
            status, payload = 500, {"error": "internal", "message": "internal error"}
            try:
                parts = urlsplit(self.path)
                length = int(self.headers.get("Content-Length") or 0)
                if length > MAX_BODY:
                    raise ApiError(413, "too_large")
                body: dict[str, Any] = {}
                if length:
                    raw = self.rfile.read(length)
                    try:
                        body = json.loads(raw.decode("utf-8")) if raw else {}
                    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                        raise ApiError(400, "bad_json") from exc
                    if not isinstance(body, dict):
                        raise ApiError(400, "bad_json")
                req = Request(ctx, method, parts.path.rstrip("/") or "/", parse_qs(parts.query),
                              self.headers, body)
                status, payload = dispatch(ctx, router, req)
            except ValidationError as exc:
                status, payload = 422, {"error": "validation", "message": "validation failed",
                                        "fields": exc.fields}
            except ApiError as exc:
                status, payload = exc.status, {"error": exc.code, "message": exc.message,
                                               "fields": exc.fields}
            except Exception:
                log.exception("unhandled API error on %s %s", method, self.path)
            data = json.dumps(payload, default=str).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            self._handle("GET")

        def do_POST(self) -> None:
            self._handle("POST")

        def do_PUT(self) -> None:
            self._handle("PUT")

        def do_DELETE(self) -> None:
            self._handle("DELETE")

    socket_path.parent.mkdir(parents=True, exist_ok=True)
    if socket_path.exists():
        socket_path.unlink()
    server = _ThreadingUnixServer(str(socket_path), RequestHandler)
    os.chmod(socket_path, 0o660)
    try:
        gid = grp.getgrnam(SOCKET_GROUP).gr_gid
        os.chown(socket_path, -1, gid)
    except (KeyError, PermissionError):
        log.warning("socket group %s not available; socket is only reachable by its owner", SOCKET_GROUP)
    return server
