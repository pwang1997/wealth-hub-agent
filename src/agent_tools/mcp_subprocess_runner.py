import os
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class McpServerProcessSpec:
    name: str
    argv: list[str]
    env: dict[str, str] = field(default_factory=dict)
    cwd: str | None = None


class McpSubprocessRunner:
    def __init__(
        self,
        specs: list[McpServerProcessSpec],
        *,
        base_env: dict[str, str] | None = None,
        log_sink: Callable[[str, str, str], None] | None = None,
    ):
        self._specs = specs
        self._base_env = base_env or {}
        self._log_sink = log_sink or self._default_log_sink

        self._processes: dict[str, subprocess.Popen] = {}
        self._threads: list[threading.Thread] = []
        self._lock = threading.Lock()

    def start_all(self) -> None:
        for spec in self._specs:
            self.start(spec)

    def start(self, spec: McpServerProcessSpec) -> None:
        with self._lock:
            if spec.name in self._processes and self._processes[spec.name].poll() is None:
                return

            env = os.environ.copy()
            env.update(self._base_env)
            env.update(spec.env)
            env.setdefault("PYTHONUNBUFFERED", "1")

            process = subprocess.Popen(
                spec.argv,
                cwd=spec.cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            self._processes[spec.name] = process

            self._threads.append(self._spawn_log_thread(spec.name, process, "stdout"))
            self._threads.append(self._spawn_log_thread(spec.name, process, "stderr"))

    def stop_all(self, *, timeout_s: float = 8.0) -> None:
        names = list(self._processes.keys())
        for name in names:
            self.stop(name, timeout_s=timeout_s)

    def stop(self, name: str, *, timeout_s: float = 8.0) -> None:
        with self._lock:
            process = self._processes.get(name)
        if process is None:
            return

        if process.poll() is not None:
            return

        try:
            process.send_signal(signal.SIGTERM)
        except ProcessLookupError:
            return

        deadline = time.time() + timeout_s
        while time.time() < deadline:
            if process.poll() is not None:
                return
            time.sleep(0.05)

        try:
            process.kill()
        except ProcessLookupError:
            return

    def wait_all(self) -> dict[str, int]:
        exit_codes: dict[str, int] = {}
        for name, process in list(self._processes.items()):
            try:
                exit_codes[name] = process.wait()
            except Exception:
                exit_codes[name] = -1
        return exit_codes

    def is_running(self, name: str) -> bool:
        process = self._processes.get(name)
        return process is not None and process.poll() is None

    def _spawn_log_thread(
        self, name: str, process: subprocess.Popen, stream: str
    ) -> threading.Thread:
        thread = threading.Thread(
            target=self._pipe_reader,
            args=(name, process, stream),
            daemon=True,
        )
        thread.start()
        return thread

    def _pipe_reader(self, name: str, process: subprocess.Popen, stream: str) -> None:
        pipe = getattr(process, stream, None)
        if pipe is None:
            return
        for line in iter(pipe.readline, ""):
            cleaned = line.rstrip("\n")
            if cleaned:
                self._log_sink(name, stream, cleaned)

    @staticmethod
    def _default_log_sink(server_name: str, stream: str, message: str) -> None:
        sys.stdout.write(f"[{server_name}][{stream}] {message}\n")
        sys.stdout.flush()
