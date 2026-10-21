#!/usr/bin/env python3
"""Serve fixture HTTP responses on 127.0.0.1 only.

Each file in --root is named <slug>.txt. A GET /<slug> returns that file.
The file format is an optional status line (HTTP/1.0 200 OK), header lines,
a blank line, then a body. This process does not open any socket except the
loopback listener.
"""

from __future__ import annotations

import argparse
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SLUG_RE_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")


class UsageError(Exception):
    pass


def parse_fixture(raw: bytes) -> tuple[int, list[tuple[str, str]], bytes]:
    text = raw.decode("utf-8-sig")
    text = text.replace("\r\n", "\n")
    if text.endswith("\n"):
        # Keep a trailing newline in the body when the blank-line split allows it.
        pass
    if "\n\n" in text:
        head, body = text.split("\n\n", 1)
    else:
        head, body = text, ""
    lines = head.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    status = 200
    if lines and lines[0].startswith("HTTP/"):
        parts = lines[0].split()
        if len(parts) < 2 or not parts[1].isdigit():
            raise UsageError("bad status line")
        status = int(parts[1])
        if not 100 <= status <= 599:
            raise UsageError("status out of range")
        lines = lines[1:]
    headers: list[tuple[str, str]] = []
    for line in lines:
        if not line.strip():
            continue
        if ":" not in line:
            raise UsageError(f"bad header line: {line!r}")
        name, value = line.split(":", 1)
        name = name.strip()
        value = value.strip()
        if not name:
            raise UsageError("empty header name")
        headers.append((name, value))
    return status, headers, body.encode("utf-8")


def make_handler(root: Path, access_log: Path | None):
    class Handler(BaseHTTPRequestHandler):
        server_version = "fixture-server/1.0"
        sys_version = ""

        def log_message(self, fmt: str, *args) -> None:
            if access_log is None:
                return
            path = urllib.parse.urlsplit(self.path).path
            with access_log.open("a", encoding="utf-8") as handle:
                handle.write(path + "\n")

        def do_GET(self) -> None:  # noqa: N802
            path = urllib.parse.urlsplit(self.path).path
            if path == "/health":
                body = b"ok\n"
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            slug = path[1:] if path.startswith("/") else path
            if not slug or any(ch not in SLUG_RE_CHARS for ch in slug):
                self.send_error(404)
                return
            file_path = root / f"{slug}.txt"
            if not file_path.is_file():
                self.send_error(404)
                return
            try:
                status, headers, body = parse_fixture(file_path.read_bytes())
            except (UsageError, UnicodeError):
                self.send_error(500)
                return
            self.send_response(status)
            seen_length = False
            for name, value in headers:
                if name.lower() == "content-length":
                    seen_length = True
                self.send_header(name, value)
            if not seen_length:
                self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_HEAD(self) -> None:  # noqa: N802
            self.do_GET()

    return Handler


class FixtureServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="fixture_server.py")
    parser.add_argument("--root", required=True, help="directory of <slug>.txt fixtures")
    parser.add_argument("--port", type=int, default=0, help="bind port, 0 picks a free port")
    parser.add_argument("--access-log", default="", help="append request paths, one per line")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(list(sys.argv[1:] if argv is None else argv))
    if not 0 <= args.port <= 65535:
        print("error: port out of range", file=sys.stderr)
        return 2
    root = Path(args.root)
    if not root.is_dir():
        print("error: root is not a directory", file=sys.stderr)
        return 2
    access = Path(args.access_log) if args.access_log else None
    if access is not None:
        access.parent.mkdir(parents=True, exist_ok=True)
        access.write_text("", encoding="utf-8")
    handler = make_handler(root.resolve(), access)
    try:
        server = FixtureServer(("127.0.0.1", args.port), handler)
    except OSError as exc:
        print(f"error: {exc.__class__.__name__}", file=sys.stderr)
        return 2
    print(f"PORT {server.server_address[1]}", flush=True)
    print("BIND 127.0.0.1", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
