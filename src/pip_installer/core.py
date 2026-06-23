import os
import shutil
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Callable, Optional

import requests
from mcdreforged.api.all import CommandSource, RColor, RText, RTextList
from zipfile import ZipFile

import pip_installer.runtime as rt
from pip_installer.runtime import DownloadState

VALID_PLUGIN_PACKAGE_FORMATS = ["mcdr", "pyz", "zip"]


# ===================== Helpers =====================


def human_size(size_bytes: float) -> str:
    if size_bytes < 1024:
        return f"{size_bytes:.0f} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def format_time(seconds: Optional[float]) -> str:
    if seconds is None:
        return "未知"
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        return f"{seconds // 60:.0f}m{seconds % 60:.0f}s"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    return f"{h}h{m}m"


# ===================== PyPI Install =====================


def run_pip_install(
    src: CommandSource, packages: list[str], quiet_mode: bool
) -> None:
    """Execute pip install, update rt.current_process, reply results."""
    src.reply(RText(f"开始安装包: {', '.join(packages)}", RColor.aqua))
    cmd: list[str] = [sys.executable, "-m", "pip", "install", *packages]
    try:
        if quiet_mode:
            rt.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = rt.current_process.communicate()
            if rt.current_process.returncode == 0:
                src.reply(RText("PyPI包安装完成！", RColor.green))
                if stdout:
                    src.reply(f"输出: {stdout}")
            else:
                src.reply(RText("PyPI包安装失败！", RColor.red))
                if stderr:
                    src.reply(f"错误: {stderr}")
        else:
            rt.current_process = subprocess.Popen(cmd)
            rt.current_process.wait()
            if rt.current_process.returncode == 0:
                src.reply(RText("PyPI包安装完成！", RColor.green))
            else:
                src.reply(RText("PyPI包安装失败！", RColor.red))
    except Exception as e:
        src.reply(RText(f"安装过程中发生错误: {str(e)}", RColor.red))
    finally:
        rt.current_process = None


def parse_requirements_from_archive(file_path: str) -> Optional[list[str]]:
    """Read requirements.txt from a plugin archive, return package list."""
    requirements_file = "requirements.txt"
    try:
        with ZipFile(file_path, "r") as zip_ref:
            if requirements_file not in zip_ref.namelist():
                return None
            with zip_ref.open(requirements_file) as f:
                content = f.read().decode("utf-8")
            packages = []
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    packages.append(line)
            return packages if packages else None
    except Exception:
        return None


# ===================== Plugin Placement =====================


def place_local_plugin(
    src: CommandSource, file_path: Path, plugins_dir: Path
) -> Optional[Path]:
    """Copy to plugins/ if needed, return the final plugin path."""
    file_path = file_path.resolve()
    if not file_path.exists():
        src.reply(RText(f"文件不存在: {file_path}", RColor.red))
        return None

    plugins_abs = plugins_dir.resolve()
    if _in_plugins(file_path, plugins_abs):
        return file_path

    dest = plugins_dir / file_path.name
    if dest.exists():
        src.reply(RText(f"插件已存在，将覆盖: {dest.name}", RColor.yellow))
    shutil.copy(str(file_path), str(dest))
    src.reply(RText(f"已复制到 plugins 目录: {dest.name}", RColor.green))
    return dest.resolve()


def place_remote_plugin(
    src: CommandSource,
    url: str,
    cache_dir: Path,
    plugins_dir: Path,
    custom_name: Optional[str],
) -> Optional[Path]:
    """Download from url → cache, move to plugins, return final path."""
    src.reply(RText(f"开始下载插件: {url}", RColor.aqua))

    rt.current_download = DownloadState(url)
    reported = False

    def _on_progress() -> None:
        nonlocal reported
        if reported:
            return
        ds = rt.current_download
        if ds is None or ds.total_bytes == 0:
            return
        elapsed = time.time() - ds._start_time
        if elapsed < 1.0:
            return
        ds.tick()
        info = RTextList(
            RText(f"已下载: {human_size(ds.downloaded_bytes)}", RColor.aqua),
        )
        pct = ds.downloaded_bytes / ds.total_bytes * 100
        info.append(
            RText(
                f" / {human_size(ds.total_bytes)} ({pct:.1f}%)",
                RColor.gray,
            )
        )
        info.append(RText(f"\n速度: {human_size(ds.speed)}/s", RColor.aqua))
        if ds.eta is not None:
            info.append(RText(f"  剩余: {format_time(ds.eta)}", RColor.gray))
        info.append(
            RText("\n使用 !!pipi plugin status 查看下载进度", RColor.gray)
        )
        src.reply(info)
        reported = True

    file_path = _download_file(
        url, cache_dir, custom_name, on_progress=_on_progress
    )

    if file_path is None:
        if rt.current_download is not None and rt.current_download.cancelled:
            src.reply(RText("插件下载已取消！", RColor.yellow))
        else:
            src.reply(RText("插件下载失败！", RColor.red))
        return None

    src.reply(RText(f"插件下载完成: {file_path.name}", RColor.green))

    dest = plugins_dir / file_path.name
    if dest.exists():
        src.reply(RText(f"插件已存在，将覆盖: {dest.name}", RColor.yellow))
    shutil.move(str(file_path), str(dest))
    return dest


def _in_plugins(file_path: Path, plugins_dir: Path) -> bool:
    try:
        return (
            str(file_path).startswith(str(plugins_dir) + os.sep)
            or file_path == plugins_dir
        )
    except Exception:
        return False


def _download_file(
    url: str,
    save_dir: Path,
    custom_name: Optional[str] = None,
    on_progress: Optional[Callable[[], None]] = None,
) -> Optional[Path]:
    """Pure download with resume support. Checks rt.current_download.cancelled."""
    try:
        parsed_url = urllib.parse.urlparse(url)
        filename = custom_name or os.path.basename(parsed_url.path)
        if not filename:
            filename = "downloaded_plugin.mcdr"

        save_path = save_dir / filename
        resume_pos = save_path.stat().st_size if save_path.exists() else 0

        headers: dict[str, str] = {}
        if resume_pos > 0:
            headers["Range"] = f"bytes={resume_pos}-"

        response = requests.get(url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()

        total = resume_pos + int(response.headers.get("content-length", 0))
        downloaded = resume_pos

        mode = "ab" if resume_pos > 0 else "wb"
        with open(save_path, mode) as f:
            for chunk in response.iter_content(chunk_size=8192):
                if (
                    rt.current_download is not None
                    and rt.current_download.cancelled
                ):
                    return None
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if rt.current_download is not None:
                        rt.current_download.update(downloaded, total)
                    if on_progress:
                        on_progress()

        return save_path
    except Exception:
        return None
