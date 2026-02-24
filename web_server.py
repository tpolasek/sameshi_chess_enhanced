#!/usr/bin/env python3
"""HTTP bridge for sameshi chess engine.

Usage:
  python3 web_server.py
  curl "http://localhost:4000/?move=e2e4"
  curl "http://localhost:4000/reset"
"""

from __future__ import annotations

import atexit
import os
import re
import select
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional
from urllib.parse import parse_qs, urlparse

ENGINE_PATH = os.environ.get("CHESS_PROGRAM", "./sameshi")
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "4000"))
READ_CHUNK_SIZE = 4096
READ_TIMEOUT_SECONDS = 300
PROMPT = "move: "
MOVE_RE = re.compile(r"^[a-h][1-8][a-h][1-8]$")


class ChessEngineBridge:
    """Keeps a single chess process alive and returns per-move stdout deltas."""

    def __init__(self, program: str) -> None:
        self.program = program
        self.proc: Optional[subprocess.Popen[bytes]] = None
        self.lock = threading.Lock()
        self._start_process()

    def _start_process(self) -> None:
        self.proc = subprocess.Popen(
            [self.program],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
        )
        self._read_until_prompt(discard=True)

    def _ensure_running(self) -> None:
        if self.proc is None or self.proc.poll() is not None:
            self._start_process()

    def _read_until_prompt(self, discard: bool = False) -> str:
        if self.proc is None or self.proc.stdout is None:
            raise RuntimeError("Chess process stdout not available")

        fd = self.proc.stdout.fileno()
        chunks: list[bytes] = []

        while True:
            ready, _, _ = select.select([fd], [], [], READ_TIMEOUT_SECONDS)
            if not ready:
                raise TimeoutError("Timed out waiting for chess engine output")

            data = os.read(fd, READ_CHUNK_SIZE)
            if not data:
                raise RuntimeError("Chess engine exited while reading output")

            chunks.append(data)
            decoded = b"".join(chunks).decode("utf-8", errors="replace")
            if PROMPT in decoded:
                before_prompt, _, _ = decoded.rpartition(PROMPT)
                return "" if discard else before_prompt

    def send_move(self, move: str) -> str:
        with self.lock:
            self._ensure_running()
            assert self.proc is not None and self.proc.stdin is not None

            self.proc.stdin.write((move + "\n").encode("utf-8"))
            self.proc.stdin.flush()
            return self._read_until_prompt(discard=False)

    def _stop_process(self) -> None:
        if self.proc is None:
            return
        if self.proc.poll() is not None:
            self.proc = None
            return
        try:
            assert self.proc.stdin is not None
            self.proc.stdin.write(b"q\n")
            self.proc.stdin.flush()
            self.proc.wait(timeout=1.0)
        except Exception:
            self.proc.kill()
        finally:
            self.proc = None

    def reset(self) -> None:
        with self.lock:
            self._stop_process()
            self._start_process()

    def close(self) -> None:
        with self.lock:
            self._stop_process()


ENGINE: Optional[ChessEngineBridge] = None
ENGINE_LOCK = threading.Lock()


def get_engine() -> ChessEngineBridge:
    global ENGINE
    with ENGINE_LOCK:
        if ENGINE is None:
            ENGINE = ChessEngineBridge(ENGINE_PATH)
            atexit.register(ENGINE.close)
        return ENGINE


class ChessHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        if parsed.path == "/reset" or params.get("reset", [""])[0] == "1":
            try:
                get_engine().reset()
            except Exception as exc:  # pragma: no cover
                self._send_text(500, f"Engine error: {exc}\n")
                return
            self._send_text(200, "Game reset\n")
            return

        move = params.get("move", [""])[0]

        if not MOVE_RE.fullmatch(move):
            self._send_text(
                400,
                "Query parameter 'move' is required in long algebraic form, "
                "for example: /?move=b2b4 (or call /reset to restart)\n",
            )
            return

        print(f"Got move {move}")
        try:
            delta = get_engine().send_move(move)
        except Exception as exc:  # pragma: no cover
            self._send_text(500, f"Engine error: {exc}\n")
            return

        self._send_text(200, delta + "\n")

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_text(self, status: int, body: str) -> None:
        body_bytes = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body_bytes)))
        self.end_headers()
        self.wfile.write(body_bytes)


def main() -> None:
    get_engine()
    server = ThreadingHTTPServer((HOST, PORT), ChessHandler)
    print(f"Serving chess bridge on http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
