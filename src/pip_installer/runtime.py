import subprocess
import time
from typing import Optional


class DownloadState:
    """Tracks a plugin download: progress, speed, cancellation."""

    def __init__(self, url: str) -> None:
        self.url: str = url
        self.downloaded_bytes: int = 0
        self.total_bytes: int = 0
        self._cancelled: bool = False
        self._start_time: float = time.time()
        self._last_bytes: int = 0
        self._last_time: float = self._start_time

    def update(self, downloaded: int, total: int) -> None:
        self.downloaded_bytes = downloaded
        if total > 0:
            self.total_bytes = total

    def tick(self) -> None:
        self._last_bytes = self.downloaded_bytes
        self._last_time = time.time()

    @property
    def speed(self) -> float:
        now = time.time()
        elapsed = now - self._last_time
        if elapsed >= 1.0:
            diff = self.downloaded_bytes - self._last_bytes
            if elapsed > 0:
                return diff / elapsed
        total_elapsed = now - self._start_time
        if total_elapsed > 0:
            return self.downloaded_bytes / total_elapsed
        return 0.0

    @property
    def eta(self) -> Optional[float]:
        s = self.speed
        if s > 0 and self.total_bytes > 0:
            return (self.total_bytes - self.downloaded_bytes) / s
        return None

    def cancel(self) -> None:
        self._cancelled = True

    @property
    def cancelled(self) -> bool:
        return self._cancelled


# PyPI install process
current_process: Optional["subprocess.Popen"] = None

# Plugin download state
current_download: Optional[DownloadState] = None
