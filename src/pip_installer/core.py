from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path, PurePosixPath
from typing import Callable, Optional
from zipfile import ZipFile

import requests
from mcdreforged.api.all import CommandSource, RColor, RText, RTextList

import pip_installer.runtime as rt
from pip_installer.runtime import DownloadState

VALID_PLUGIN_PACKAGE_FORMATS = ["mcdr", "pyz", "zip"]


# ===================== Helpers =====================


def is_valid_plugin_package(file_path: Path) -> bool:
    return file_path.suffix.removeprefix(".") in VALID_PLUGIN_PACKAGE_FORMATS


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
) -> bool:
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
                return True
            else:
                src.reply(RText("PyPI包安装失败！", RColor.red))
                if stderr:
                    src.reply(f"错误: {stderr}")
                return False
        else:
            rt.current_process = subprocess.Popen(cmd)
            rt.current_process.wait()
            if rt.current_process.returncode == 0:
                src.reply(RText("PyPI包安装完成！", RColor.green))
                return True
            else:
                src.reply(RText("PyPI包安装失败！", RColor.red))
                return False
    except Exception as e:  # noqa: BLE001
        src.reply(RText(f"安装过程中发生错误: {e!s}", RColor.red))
        return False
    finally:
        rt.current_process = None


def install_pypi_packages(src: CommandSource, package_text: str) -> bool:
    packages: list[str] = package_text.split()
    quiet_mode = "-q" in packages
    if quiet_mode:
        packages.remove("-q")
    return run_pip_install(src, packages, quiet_mode)


def decode_text(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("gbk")


def extract_requirements_from_archive(
    file_path: str, target_dir: Path
) -> Optional[Path]:
    requirements_file = "requirements.txt"
    with ZipFile(file_path, "r") as zip_ref:
        if requirements_file not in zip_ref.namelist():
            return None
        with zip_ref.open(requirements_file) as f:
            content = decode_text(f.read())
    archive_hash = hashlib.sha256(
        str(Path(file_path).resolve()).encode()
    ).hexdigest()
    requirements_path = target_dir / f"{archive_hash}.requirements.txt"
    requirements_path.write_text(content, encoding="utf-8")
    return requirements_path


def install_requirements_from_file(
    src: CommandSource, file_path: Path
) -> bool:
    if file_path.name == "*":
        src.reply("正在检测并安装插件目录中所有打包插件的Python(PyPI)包依赖……")
        plugins_dir = Path("plugins")
        if not plugins_dir.exists():
            src.reply(RText("plugins 目录不存在！", RColor.yellow))
            return False

        cache_dir = Path(".cache") / "requirements"
        cache_dir.mkdir(parents=True, exist_ok=True)
        requirement_args: list[str] = []
        for plugin_path in plugins_dir.iterdir():
            if not plugin_path.is_file():
                continue
            if not is_valid_plugin_package(plugin_path):
                continue
            requirements_path, read_success = _read_requirements_from_archive(
                src, plugin_path, cache_dir
            )
            if not read_success:
                continue
            if requirements_path is not None:
                requirement_args.extend(["-r", str(requirements_path)])

        if not requirement_args:
            src.reply(
                RText("plugins 目录中没有可安装的插件依赖！", RColor.yellow)
            )
            return True

        return run_pip_install(src, requirement_args, False)

    file_suffix = file_path.suffix.removeprefix(".")
    if file_suffix == "txt":
        if not file_path.exists():
            src.reply(RText(f"依赖文件不存在: {file_path}", RColor.red))
            return False
        return run_pip_install(src, ["-r", str(file_path)], False)

    if file_suffix not in VALID_PLUGIN_PACKAGE_FORMATS:
        src.reply(
            RText(
                "文件格式无效，请使用 txt, mcdr, pyz 或 zip 格式！",
                RColor.red,
            )
        )
        return False

    cache_dir = Path(".cache") / "requirements"
    cache_dir.mkdir(parents=True, exist_ok=True)
    requirements_path, read_success = _read_requirements_from_archive(
        src, file_path, cache_dir
    )
    if not read_success:
        return False
    if requirements_path is None:
        src.reply(
            RText(
                "插件包中没有 requirements.txt 文件或文件为空！",
                RColor.yellow,
            )
        )
        return True

    return run_pip_install(src, ["-r", str(requirements_path)], False)


def _read_requirements_from_archive(
    src: CommandSource, file_path: Path, cache_dir: Path
) -> tuple[Optional[Path], bool]:
    try:
        return extract_requirements_from_archive(
            str(file_path), cache_dir
        ), True
    except Exception as e:  # noqa: BLE001
        src.reply(RText(f"读取插件依赖失败: {e!s}", RColor.red))
        return None, False


# ===================== Plugin Placement =====================


def place_local_plugin(
    src: CommandSource, file_path: Path, plugins_dir: Path
) -> Optional[Path]:
    """Copy to plugins/ if needed, return the final plugin path."""
    file_path = file_path.resolve()
    if not file_path.exists():
        src.reply(RText(f"文件不存在: {file_path}", RColor.red))
        return None
    if not is_valid_plugin_package(file_path):
        src.reply(
            RText("插件包格式无效，请使用 mcdr, pyz 或 zip 格式！", RColor.red)
        )
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
    parsed_url = urllib.parse.urlparse(url)
    filename = custom_name or PurePosixPath(parsed_url.path).name
    if not filename:
        filename = "downloaded_plugin.mcdr"
    if not is_valid_plugin_package(Path(filename)):
        src.reply(
            RText("插件包格式无效，请使用 mcdr, pyz 或 zip 格式！", RColor.red)
        )
        return None

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
        url, cache_dir, filename, on_progress=_on_progress
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
    return dest.resolve()


def install_plugin(
    src: CommandSource, file_url: str, custom_name: Optional[str]
) -> None:
    """Install a plugin from a remote URL or local path, then handle deps."""
    plugins_dir = Path("plugins")
    cache_dir = Path(".cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    plugins_dir.mkdir(parents=True, exist_ok=True)

    try:
        if file_url.startswith(("http://", "https://")):
            file_path = place_remote_plugin(
                src, file_url, cache_dir, plugins_dir, custom_name
            )
        else:
            file_path = place_local_plugin(src, Path(file_url), plugins_dir)
        if file_path is None:
            return

        rt.current_download = None
        if (
            rt.current_process is not None
            and rt.current_process.poll() is None
        ):
            src.reply(
                RText(
                    "已有安装进程在运行中，已跳过自动处理插件依赖。",
                    RColor.yellow,
                )
            )
            src.reply(
                RTextList(
                    RText("安装进程结束后，可手动执行: "),
                    RText(f"!!pipi -r {file_path!s}", RColor.yellow),
                )
            )
            _reply_plugin_load_commands(src, file_path)
            return

        src.reply(RText(f"开始处理插件依赖: {file_path.name}", RColor.aqua))
        dependencies_ready = install_requirements_from_file(src, file_path)
        if dependencies_ready:
            src.reply(
                RText(
                    "插件依赖处理已结束；若存在依赖，请确认安装成功后再加载插件。",
                    RColor.green,
                )
            )
        else:
            src.reply(
                RText(
                    "插件依赖处理失败或未完成；请解决依赖问题后再加载插件。",
                    RColor.yellow,
                )
            )
        _reply_plugin_load_commands(src, file_path)
    except Exception as e:  # noqa: BLE001
        src.reply(RText(f"插件安装发生错误: {e!s}", RColor.red))
    finally:
        rt.current_download = None


def _reply_plugin_load_commands(src: CommandSource, file_path: Path) -> None:
    src.reply(
        RTextList(
            RText("你可以选用以下命令加载新安装的第三方插件: \n"),
            RText(f"!!MCDR plugin load {file_path.name}\n", RColor.yellow),
            RText("!!MCDR reload plugin", RColor.yellow),
            RText(" - 重载所有变更插件", RColor.gray),
        )
    )


def _in_plugins(file_path: Path, plugins_dir: Path) -> bool:
    try:
        file_path.relative_to(plugins_dir)
        return True
    except ValueError:
        return file_path == plugins_dir


def _download_file(
    url: str,
    save_dir: Path,
    filename: str,
    on_progress: Optional[Callable[[], None]] = None,
) -> Optional[Path]:
    """Pure download with resume support. Checks rt.current_download.cancelled."""
    save_path = save_dir / filename
    resume_pos = save_path.stat().st_size if save_path.exists() else 0

    headers: dict[str, str] = {}
    if resume_pos > 0:
        headers["Range"] = f"bytes={resume_pos}-"

    response = requests.get(url, headers=headers, stream=True, timeout=30)
    response.raise_for_status()

    # Verify server accepted range request; redownload if not supported
    if resume_pos > 0 and response.status_code != 206:
        resume_pos = 0
        save_path.unlink(missing_ok=True)

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
