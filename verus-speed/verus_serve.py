#!/usr/bin/env python3
"""Client for resident Verus verifier processes (`rust_verify --internal-serve`).

A resident process verifies one request at a time but stays alive between
requests, so process start, loading the rustc library and (with the import
cache) deserializing vstd.vir are paid once. `Pool` keeps N such processes,
restarts one after a crash or timeout, and can answer repeated identical
requests from a response cache, like AXLE's `cached_response`.

Protocol: one JSON line per request on stdin, {"cwd": ..., "args": [...]};
the server writes the normal Verus stdout and then a line starting with
SENTINEL followed by {"rc": N}. Verus diagnostics stay on stderr.

  pool = Pool(["rustup", "run", "1.88.0", RUST_VERIFY], size=8)
  r = pool.run(cwd, ["candidate.rs", "--output-json"])   # {"rc", "stdout", "stderr", "wall_s", ...}
"""
from __future__ import annotations

import hashlib
import json
import os
import queue
import selectors
import subprocess
import threading
import time
from pathlib import Path

SENTINEL = "\x1eVERUS-SERVE-DONE "
CACHE = Path.home() / ".cache/verus-skill"


def verus_env(extra: dict | None = None) -> dict:
    env = dict(os.environ)
    env["RUSTUP_HOME"] = str(CACHE / "rustup")
    env["CARGO_HOME"] = str(CACHE / "cargo")
    env["PATH"] = f"{CACHE / 'cargo/bin'}:{env.get('PATH', '')}"
    env["VERUS_IMPORT_CACHE"] = "1"
    env.update(extra or {})
    return env


class Worker:
    def __init__(self, command: list[str], env: dict):
        self.command, self.env = command, env
        self.proc: subprocess.Popen | None = None
        self.served = 0

    def start(self) -> None:
        self.proc = subprocess.Popen([*self.command, "--internal-serve"], stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=self.env,
                                     text=True, start_new_session=True)
        self.served = 0

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            try:
                os.killpg(self.proc.pid, 9)
            except ProcessLookupError:
                pass
            self.proc.wait()
        self.proc = None

    def run(self, cwd: str, args: list[str], timeout: float) -> dict:
        if self.proc is None or self.proc.poll() is not None:
            self.start()
        t0 = time.monotonic()
        self.proc.stdin.write(json.dumps({"cwd": cwd, "args": args}) + "\n")
        self.proc.stdin.flush()
        # Raw reads: a partial line (e.g. a progress note without newline) must never block.
        fds = {self.proc.stdout.fileno(): bytearray(), self.proc.stderr.fileno(): bytearray()}
        out_fd = self.proc.stdout.fileno()
        sentinel = SENTINEL.encode()
        sel = selectors.DefaultSelector()
        for fd in fds:
            sel.register(fd, selectors.EVENT_READ)
        rc = None
        try:
            while rc is None:
                left = timeout - (time.monotonic() - t0)
                if left <= 0:
                    self.stop()
                    return self._result(None, fds, out_fd, t0, timed_out=True)
                for key, _ in sel.select(timeout=min(left, 1.0)):
                    chunk = os.read(key.fd, 1 << 16)
                    if not chunk:
                        self.stop()
                        return self._result(None, fds, out_fd, t0, crashed=True)
                    fds[key.fd] += chunk
                buf = fds[out_fd]
                i = buf.find(sentinel)
                if i >= 0 and buf.find(b"\n", i) >= 0:
                    j = buf.find(b"\n", i)
                    rc = json.loads(buf[i + len(sentinel):j])["rc"]
                    del buf[i:j + 1]
            # stderr written just before the sentinel may still be in flight
            for key, _ in sel.select(timeout=0.02):
                if key.fd != out_fd:
                    fds[key.fd] += os.read(key.fd, 1 << 16)
        finally:
            sel.close()
        self.served += 1
        return self._result(rc, fds, out_fd, t0)

    @staticmethod
    def _result(rc, fds, out_fd, t0, **flags) -> dict:
        err_fd = next(fd for fd in fds if fd != out_fd)
        return {"rc": rc, "stdout": fds[out_fd].decode(errors="replace"),
                "stderr": fds[err_fd].decode(errors="replace"), "wall_s": time.monotonic() - t0, **flags}


class Pool:
    """`command` starts rust_verify, e.g. ["rustup", "run", "1.88.0", ".../rust_verify"]."""

    def __init__(self, command: list[str], size: int = 8, env: dict | None = None, cache: bool = False,
                 max_requests_per_worker: int = 500):
        self.command, self.env = command, verus_env(env)
        self.free: queue.Queue[Worker] = queue.Queue()
        for _ in range(size):
            self.free.put(Worker(command, self.env))
        self.cache_on = cache
        self.cache: dict[str, dict] = {}
        self.lock = threading.Lock()
        self.max_requests = max_requests_per_worker

    @staticmethod
    def key(cwd: str, args: list[str]) -> str:
        h = hashlib.sha256()
        h.update(json.dumps(args).encode())
        for a in args:
            p = Path(cwd) / a
            if a.endswith(".rs") and p.is_file():
                h.update(p.read_bytes())
        return h.hexdigest()

    def run(self, cwd: str, args: list[str], timeout: float = 900) -> dict:
        k = self.key(cwd, args) if self.cache_on else None
        if k:
            with self.lock:
                if k in self.cache:
                    return {**self.cache[k], "cached_response": True, "wall_s": 0.0}
        w = self.free.get()
        try:
            r = w.run(cwd, args, timeout)
            if w.served >= self.max_requests:
                w.stop()  # bound memory growth of a long-lived process
        finally:
            self.free.put(w)
        if k and r.get("rc") is not None:
            with self.lock:
                self.cache[k] = r
        return r

    def close(self) -> None:
        while not self.free.empty():
            self.free.get().stop()
