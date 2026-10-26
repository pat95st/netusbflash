"""Test helpers: a running service in simulation mode and a small API client."""

from __future__ import annotations

import http.client
import json
import shutil
import socket
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from netusbflash.api import Router, make_server
from netusbflash.config import Paths
from netusbflash.handlers import register
from netusbflash.service import Context


class UnixHTTPConnection(http.client.HTTPConnection):
    def __init__(self, path: str):
        super().__init__("localhost", timeout=30)
        self.unix_path = path

    def connect(self) -> None:
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.unix_path)


class Client:
    def __init__(self, socket_path: str):
        self.socket_path = socket_path
        self.token: str | None = None
        self.setup_code: str | None = None

    def call(self, method: str, path: str, body: dict[str, Any] | None = None) -> tuple[int, Any]:
        conn = UnixHTTPConnection(self.socket_path)
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["X-Session-Token"] = self.token
        if self.setup_code:
            headers["X-Setup-Code"] = self.setup_code
        data = json.dumps(body).encode() if body is not None else None
        conn.request(method, "/api/v1" + path, body=data, headers=headers)
        resp = conn.getresponse()
        payload = json.loads(resp.read().decode() or "{}")
        conn.close()
        return resp.status, payload


class ServiceFixture:
    """Starts the API and workers in a temp directory with a simulated gadget."""

    def __init__(self) -> None:
        # Unix socket paths are limited to ~108 characters, so keep this short.
        self.tmp = Path(tempfile.mkdtemp(prefix="nuf"))
        self.paths = Paths(etc=self.tmp / "etc", lib=self.tmp / "lib", run=self.tmp / "run")
        self.ctx = Context(self.paths, simulated=True)
        self.ctx.setup.ensure_code()
        router = Router()
        register(router, self.ctx)
        self.server = make_server(self.ctx, router, self.paths.socket)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.1},
                                       daemon=True)
        self.thread.start()
        self.client = Client(str(self.paths.socket))

    def start_workers(self) -> None:
        for worker in (self.ctx.monitor, self.ctx.uploader, self.ctx.mailer):
            worker.start()

    def complete_setup(self, password: str = "correct-horse-battery") -> None:
        c = self.client
        c.setup_code = self.ctx.setup.read_code()
        assert c.call("POST", "/setup/admin", {"username": "admin", "email": "admin@example.com",
                                               "password": password, "locale": "en"})[0] == 200
        assert c.call("POST", "/setup/system", {"hostname": "nuf-test", "timezone": "UTC"})[0] == 200
        assert c.call("POST", "/setup/usb", {"size_mb": 128, "filesystem": "exfat",
                                             "label": "REC", "idle_seconds": 5})[0] == 200
        assert c.call("POST", "/setup/target", {"skip": True})[0] == 200
        assert c.call("POST", "/setup/smtp", {"skip": True})[0] == 200
        status, body = c.call("POST", "/setup/finish", {})
        assert status == 200, body
        c.setup_code = None
        status, body = c.call("POST", "/auth/login", {"username": "admin", "password": password})
        assert status == 200, body
        c.token = body["token"]

    def close(self) -> None:
        for worker in (self.ctx.monitor, self.ctx.uploader, self.ctx.mailer):
            worker.stop()
        self.server.shutdown()
        self.server.server_close()
        shutil.rmtree(self.tmp, ignore_errors=True)


def wait_for(predicate, timeout: float = 15.0, interval: float = 0.2) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False
