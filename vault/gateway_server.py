"""Bounded HTTP server runtime for Vault Gateway."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import time
from typing import Any


DEFAULT_GATEWAY_MAX_WORKERS = 32
DEFAULT_GATEWAY_SHUTDOWN_TIMEOUT_SECONDS = 10.0


class BoundedThreadPoolHTTPServer(ThreadingHTTPServer):
    """ThreadingHTTPServer variant with bounded workers and drain mode."""

    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        request_handler_class: type[BaseHTTPRequestHandler],
        *,
        max_workers: int,
        shutdown_timeout_seconds: float = DEFAULT_GATEWAY_SHUTDOWN_TIMEOUT_SECONDS,
    ):
        super().__init__(server_address, request_handler_class)
        self.max_workers = max(1, int(max_workers or DEFAULT_GATEWAY_MAX_WORKERS))
        self.shutdown_timeout_seconds = max(0.0, float(shutdown_timeout_seconds))
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="vault-gateway")
        self._worker_slots = threading.BoundedSemaphore(self.max_workers)
        self._draining = threading.Event()
        self._active_condition = threading.Condition()
        self._active_requests = 0

    def process_request(self, request: Any, client_address: Any) -> None:
        if self.is_draining:
            self._reject_draining(request)
            return
        if not self._worker_slots.acquire(blocking=False):
            self._reject_overloaded(request)
            return
        self._increment_active()
        try:
            self._executor.submit(self._process_request_with_slot, request, client_address)
        except RuntimeError:
            self._decrement_active()
            self._worker_slots.release()
            self.shutdown_request(request)

    def server_close(self) -> None:
        self.begin_draining()
        completed = self.wait_for_active_requests(timeout=self.shutdown_timeout_seconds)
        try:
            super().server_close()
        finally:
            self._executor.shutdown(wait=completed, cancel_futures=not completed)

    @property
    def is_draining(self) -> bool:
        return self._draining.is_set()

    @property
    def active_requests(self) -> int:
        with self._active_condition:
            return self._active_requests

    def begin_draining(self) -> None:
        self._draining.set()

    def wait_for_active_requests(self, *, timeout: float | None = None) -> bool:
        deadline = None if timeout is None else time.monotonic() + max(0.0, float(timeout))
        with self._active_condition:
            while self._active_requests > 0:
                if deadline is None:
                    self._active_condition.wait()
                    continue
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self._active_condition.wait(timeout=remaining)
            return True

    def _process_request_with_slot(self, request: Any, client_address: Any) -> None:
        try:
            self.process_request_thread(request, client_address)
        finally:
            self._decrement_active()
            self._worker_slots.release()

    def _increment_active(self) -> None:
        with self._active_condition:
            self._active_requests += 1

    def _decrement_active(self) -> None:
        with self._active_condition:
            self._active_requests = max(0, self._active_requests - 1)
            if self._active_requests == 0:
                self._active_condition.notify_all()

    def _reject_overloaded(self, request: Any) -> None:
        self._reject_service_unavailable(
            request,
            error="gateway_overloaded",
            message="Gateway worker pool is full; retry later.",
        )

    def _reject_draining(self, request: Any) -> None:
        self._reject_service_unavailable(
            request,
            error="gateway_draining",
            message="Gateway is draining for shutdown; retry after restart.",
        )

    def _reject_service_unavailable(self, request: Any, *, error: str, message: str) -> None:
        body = json.dumps(
            {
                "ok": False,
                "status": "blocked",
                "error": error,
                "message": message,
            }
        ).encode("utf-8")
        try:
            request.sendall(
                b"HTTP/1.1 503 Service Unavailable\r\n"
                b"Connection: close\r\n"
                b"Content-Type: application/json; charset=utf-8\r\n"
                b"X-Content-Type-Options: nosniff\r\n"
                b"Referrer-Policy: no-referrer\r\n"
                + f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
                + body
            )
        finally:
            self.shutdown_request(request)
