"""Command Execution Engine.

Handles subprocess execution with real-time streaming, timeouts,
retry logic for transient failures, and output redaction.
"""

import os
import subprocess
import sys
import threading
import time
from typing import IO, Callable, Iterable, List, Optional, Tuple

from multi_ci_tools.exceptions import CommandError


class Redactor:
    """Strips sensitive values from command output streams."""

    def __init__(self, secrets: Iterable[str]) -> None:
        self.secrets = [s for s in secrets if s]

    def redact(self, text: str) -> str:
        """Replace known secrets with '***'."""
        for secret in self.secrets:
            if secret:
                text = text.replace(secret, "***")
        return text


class StreamReader(threading.Thread):
    """Reads a subprocess stream line-by-line in a background thread.
    
    Streams the output dynamically to a provided callback (e.g. sys.stdout.write)
    so output is not buffered until completion.
    """

    def __init__(
        self,
        stream: Optional[IO[bytes]],
        callback: Callable[[str], None],
        redactor: Optional[Redactor] = None,
    ) -> None:
        super().__init__(daemon=True)
        self.stream = stream
        self.callback = callback
        self.redactor = redactor
        self.output_buffer: List[str] = []

    def run(self) -> None:
        if not self.stream:
            return

        for line_bytes in self.stream:
            # Decode carefully to handle potentially corrupt binary output
            try:
                line = line_bytes.decode("utf-8", errors="replace")
            except Exception:
                line = line_bytes.decode("ascii", errors="ignore")

            if self.redactor:
                line = self.redactor.redact(line)

            self.output_buffer.append(line)
            self.callback(line)

    def get_output(self) -> str:
        """Return the full collected output stream."""
        return "".join(self.output_buffer)


class CommandExecutor:
    """Executes shell commands with timeouts, retries, and streaming."""

    def __init__(
        self,
        env: Optional[dict[str, str]] = None,
        secrets: Optional[Iterable[str]] = None,
    ) -> None:
        self.env = env if env is not None else dict(os.environ)
        self.redactor = Redactor(secrets) if secrets else Redactor([])

    def _execute_once(
        self,
        command: str | List[str],
        timeout_seconds: int,
        shell: bool = False,
    ) -> Tuple[int, str, str]:
        """A single execution attempt."""
        start_time = time.monotonic()
        
        proc = subprocess.Popen(
            command,
            shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.env,
        )

        def _write_stdout(line: str) -> None:
            sys.stdout.write(line)
            sys.stdout.flush()

        def _write_stderr(line: str) -> None:
            sys.stderr.write(line)
            sys.stderr.flush()

        stdout_reader = StreamReader(proc.stdout, _write_stdout, self.redactor)
        stderr_reader = StreamReader(proc.stderr, _write_stderr, self.redactor)

        stdout_reader.start()
        stderr_reader.start()

        timed_out = False
        try:
            exit_code = proc.wait(timeout=timeout_seconds if timeout_seconds > 0 else None)
        except subprocess.TimeoutExpired:
            timed_out = True
            proc.kill()
            exit_code = proc.wait()

        stdout_reader.join(timeout=2)
        stderr_reader.join(timeout=2)

        duration = time.monotonic() - start_time
        cmd_str = command if isinstance(command, str) else " ".join(command)

        if timed_out:
            raise CommandError(
                command=cmd_str,
                exit_code=exit_code,
                stdout=stdout_reader.get_output(),
                stderr=stderr_reader.get_output(),
                duration=duration,
                timed_out=True,
            )

        if exit_code != 0:
            raise CommandError(
                command=cmd_str,
                exit_code=exit_code,
                stdout=stdout_reader.get_output(),
                stderr=stderr_reader.get_output(),
                duration=duration,
                timed_out=False,
            )

        return exit_code, stdout_reader.get_output(), stderr_reader.get_output()

    def run(
        self,
        command: str | List[str],
        timeout_seconds: int = 0,
        retries: int = 0,
        shell: bool = False,
    ) -> str:
        """Run a command, with optional retries on failure."""
        attempts = 0
        max_attempts = retries + 1
        last_error = None

        while attempts < max_attempts:
            if attempts > 0:
                print(f"--- Retrying command (attempt {attempts + 1}/{max_attempts}) ---")
                time.sleep(2 ** attempts)

            try:
                _, stdout, _ = self._execute_once(command, timeout_seconds, shell)
                return stdout
            except CommandError as e:
                last_error = e
                attempts += 1
                
                if e.timed_out:
                    print(f"--- Command timed out after {timeout_seconds}s. Not retrying. ---")
                    break

        raise last_error  # type: ignore

