"""Exception hierarchy for Multi-CI-Tools.

Every exception carries context for debugging. The hierarchy is:

    MultiCIError (base)
    ├── ConfigError          — Invalid or missing configuration
    ├── AdapterError         — CI adapter detection/init failed
    ├── StageError           — A pipeline stage failed
    ├── CommandError         — A subprocess command failed
    └── NotificationError   — Notification delivery failed (non-fatal)
"""

from __future__ import annotations


class MultiCIError(Exception):
    """Base exception for all Multi-CI-Tools errors."""


class ConfigError(MultiCIError):
    """Invalid or missing configuration.

    Raised when env vars are malformed, required settings are missing,
    or conflicting options are provided.
    """

    def __init__(self, message: str, setting: str | None = None) -> None:
        self.setting = setting
        detail = f" (setting: {setting})" if setting else ""
        super().__init__(f"Configuration error{detail}: {message}")


class AdapterError(MultiCIError):
    """CI adapter detection or initialization failed.

    Raised when environment variables are inconsistent or when
    adapter-specific operations fail (e.g., reading GHA event JSON).
    """


class StageError(MultiCIError):
    """A pipeline stage failed.

    Carries the stage name and exit code for result classification.
    """

    def __init__(
        self,
        stage_name: str,
        message: str,
        exit_code: int = 1,
    ) -> None:
        self.stage_name = stage_name
        self.exit_code = exit_code
        super().__init__(f"Stage '{stage_name}' failed: {message}")


class CommandError(MultiCIError):
    """A subprocess command failed.

    Carries full execution context: command, exit code, output, timing.
    Used by the executor when a command returns non-zero or times out.
    """

    def __init__(
        self,
        command: str,
        exit_code: int,
        stdout: str = "",
        stderr: str = "",
        duration: float = 0.0,
        timed_out: bool = False,
    ) -> None:
        self.command = command
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.duration = duration
        self.timed_out = timed_out

        if timed_out:
            msg = f"Command timed out after {duration:.1f}s: {command}"
        else:
            msg = f"Command failed (exit {exit_code}): {command}"
        super().__init__(msg)


class NotificationError(MultiCIError):
    """Notification delivery failed.

    This is always non-fatal — notification failures are logged
    but never crash the pipeline.
    """

    def __init__(self, channel: str, message: str) -> None:
        self.channel = channel
        super().__init__(f"Notification failed [{channel}]: {message}")
