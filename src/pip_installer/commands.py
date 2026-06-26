import subprocess
from pathlib import Path
from typing import Optional

from mcdreforged.api.all import (
    CommandContext,
    CommandSource,
    GreedyText,
    PluginServerInterface,
    RColor,
    RText,
    RTextList,
    SimpleCommandBuilder,
    Text,
    new_thread,
)

import pip_installer.core as core
import pip_installer.runtime as rt

VALID_PLUGIN_PACKAGE_FORMATS = core.VALID_PLUGIN_PACKAGE_FORMATS
builder = SimpleCommandBuilder()


def command_register(server: PluginServerInterface):
    builder.arg("file", Text)
    builder.arg("file_url", Text)
    builder.arg("file_name", Text)
    builder.arg("package", GreedyText)
    builder.register(server)


# ===================== Help Commands =====================


@builder.command("!!pipi")
@builder.command("!!pipi help")
@builder.command("!!pipi usage")
def on_command_main(src: CommandSource, ctx: CommandContext):
    _cmd_pipi = RText("!!pipi", RColor.yellow)
    _cmd_pipi_help = RText("!!pipi help", RColor.yellow)
    _cmd_pipi_package = RText("!!pipi <package>", RColor.yellow)
    _cmd_pipi_required = RText("!!pipi -r <file>", RColor.yellow)
    _cmd_pipi_plugin = RText("!!pipi plugin <file_url>", RColor.yellow)
    _cmd_pipi_plugin_status = RText("!!pipi plugin status", RColor.yellow)
    _cmd_pip_usage = RText("!!pip usage", RColor.yellow)
    _cmd_pip = RText("!!pip", RColor.yellow)
    info = RTextList(
        RText("注意：此插件需要在控制台使用。\n", RColor.aqua),
        _cmd_pipi,
        RText(" - 查看此帮助页面\n"),
        _cmd_pipi_help,
        RText(" - 查看此帮助页面\n"),
        _cmd_pipi_package,
        RText(" - 安装Python（PyPI）包\n"),
        _cmd_pipi_required,
        RText(" - 从 (插件包内的) requirements.txt 文件安装Python(PyPI)包\n"),
        _cmd_pipi_plugin,
        RText(" - 从指定的远程文件 URL 安装插件\n"),
        _cmd_pipi_plugin_status,
        RText(" - 查看插件下载进程状态\n"),
        _cmd_pip_usage,
        RText(" - 查看"),
        _cmd_pip,
        RText("命令的用法\n"),
    )
    src.reply(info)


@builder.command("!!pip usage")
@builder.command("!!pip")
def on_command_usage_pip(src: CommandSource, ctx: CommandContext):
    _cmd_pip = RText("!!pip", RColor.yellow)
    _cmd_pip_usage = RText("!!pip usage", RColor.yellow)
    _cmd_pip_install = RText("!!pip install <package>", RColor.yellow)
    _cmd_pip_required = RText("!!pip install -r <file>", RColor.yellow)
    _cmd_pip_cancel = RText("!!pip cancel", RColor.yellow)
    _cmd_pip_status = RText("!!pip status", RColor.yellow)
    info = RTextList(
        RText(
            "注意：此命令需要在 MCDR 控制台使用，用法和 shell 中的 pip 命令有所不同。\n",
            RColor.aqua,
        ),
        _cmd_pip,
        RText(" - 查看此帮助页面\n"),
        _cmd_pip_usage,
        RText(" - 查看此帮助页面\n"),
        _cmd_pip_install,
        RText(" - 安装Python(PyPI)包\n"),
        _cmd_pip_required,
        RText(" - 从 (插件包内的) requirements.txt 安装Python(PyPI)包\n"),
        _cmd_pip_cancel,
        RText(" - 取消当前正在运行的安装进程\n"),
        RText("* 若支持命令别名，可以使用 !!pipc\n", RColor.gray),
        _cmd_pip_status,
        RText(" - 查看当前正在运行的安装进程状态\n"),
        RText("* 若支持命令别名，可以使用 !!pips", RColor.gray),
    )
    src.reply(info)


# ===================== PyPI Install =====================


def _console_only(src: CommandSource) -> bool:
    if not src.is_console:
        src.reply(RText("请在控制台中运行此命令！", RColor.red))
        return False
    return True


def _install_busy(src: CommandSource) -> bool:
    if rt.current_process is not None and rt.current_process.poll() is None:
        src.reply(
            RText(
                "已有安装进程在运行中，请等待完成或使用 !!pip cancel 取消！",
                RColor.yellow,
            )
        )
        return True
    return False


@builder.command("!!pip install <package>")
@builder.command("!!pipi <package>")
@new_thread("PiPInstaller:Install")
def on_install_pypi(src: CommandSource, ctx: CommandContext):
    if not _console_only(src) or _install_busy(src):
        return
    packages: list[str] = ctx["package"].split()
    quiet_mode = "-q" in packages
    if quiet_mode:
        packages.remove("-q")
    core.run_pip_install(src, packages, quiet_mode)


@builder.command("!!pip install -r <file>")
@builder.command("!!pipi -r <file>")
def on_install_required(src: CommandSource, ctx: CommandContext):
    server = src.get_server().psi()
    file_path = Path(ctx["file"])
    if not _console_only(src) or _install_busy(src):
        return
    if file_path.name != "requirements.txt":
        file_suffix = file_path.suffix.removeprefix(".")
        if file_suffix not in VALID_PLUGIN_PACKAGE_FORMATS:
            src.reply(
                RText(
                    "插件包格式无效，请使用 mcdr, pyz 或 zip 格式！",
                    RColor.red,
                )
            )
            return

    packages = core.parse_requirements_from_archive(file_path)
    if packages is None:
        src.reply(
            RText(
                "插件包中没有 requirements.txt 文件或文件为空！",
                RColor.yellow,
            )
        )
        return

    server.execute_command(f"!!pip install {' '.join(packages)}")


# ===================== Plugin Install =====================


@builder.command("!!pipi plugin <file_url>")
@builder.command("!!pipi plugin <file_url> -o <file_name>")
@new_thread("PiPInstaller:PluginInstall")
def on_install_plugin(src: CommandSource, ctx: CommandContext):
    """从远程 URL 或本地路径安装插件"""
    if not _console_only(src):
        return
    if rt.current_download is not None:
        src.reply(RText("已有插件下载进程在运行中！", RColor.yellow))
        return
    if _install_busy(src):
        return

    server = src.get_server().psi()
    file_url = ctx["file_url"]
    custom_name: Optional[str] = ctx.get("file_name")

    plugins_dir = Path("plugins")
    cache_dir = Path(".cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    plugins_dir.mkdir(parents=True, exist_ok=True)

    try:
        if file_url.startswith(("http://", "https://")):
            file_path = core.place_remote_plugin(
                src, file_url, cache_dir, plugins_dir, custom_name
            )
        else:
            file_path = core.place_local_plugin(
                src, Path(file_url), plugins_dir
            )
        if file_path is None:
            return

        src.reply(RText(f"开始处理插件依赖: {file_path.name}", RColor.aqua))
        server.execute_command(f"!!pip install -r {str(file_path)}")
        src.reply(
            RText(
                "插件依赖正在后台安装，完成后，请按以下方式手动加载插件。",
                RColor.green,
            )
        )
        src.reply(
            RTextList(
                RText("你可以选用以下命令加载新安装的第三方插件: \n"),
                RText(f"!!MCDR plg load {file_path.name}\n", RColor.yellow),
                RText("!!MCDR reload plg", RColor.yellow),
                RText(" - 重载所有变更插件", RColor.gray),
            )
        )
    except Exception as e:
        src.reply(RText(f"插件安装发生错误: {str(e)}", RColor.red))
    finally:
        rt.current_download = None


# ===================== Process Management =====================


@builder.command("!!pip cancel")
def on_cancel_install(src: CommandSource, ctx: CommandContext):
    """取消当前正在进行的进程（安装或下载）"""
    if not _console_only(src):
        return
    if rt.current_download is not None:
        rt.current_download.cancel()
        src.reply(RText("插件下载进程已取消！", RColor.green))
        rt.current_download = None
        return
    if rt.current_process is None or rt.current_process.poll() is not None:
        src.reply(RText("当前没有正在运行的进程！", RColor.yellow))
        return
    try:
        rt.current_process.terminate()
        try:
            rt.current_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            rt.current_process.kill()
            rt.current_process.wait()
        src.reply(RText("安装进程已成功取消！", RColor.green))
    except Exception as e:
        src.reply(RText(f"取消安装时发生错误: {str(e)}", RColor.red))
    finally:
        rt.current_process = None


@builder.command("!!pip status")
def on_install_status(src: CommandSource, ctx: CommandContext):
    """查看 !!pip 安装器进程状态"""
    if not _console_only(src):
        return
    if rt.current_process is None:
        src.reply(RText("当前没有正在运行的安装进程", RColor.gray))
    elif rt.current_process.poll() is None:
        src.reply(RText("安装进程正在运行中...", RColor.yellow))
        src.reply(RText("使用 !!pip cancel 可以取消安装", RColor.gray))
    else:
        return_code = rt.current_process.returncode
        if return_code == 0:
            src.reply(RText("最近的安装进程已成功完成", RColor.green))
        else:
            src.reply(
                RText(
                    f"最近的安装进程失败 (退出码: {return_code})", RColor.red
                )
            )


@builder.command("!!pipi plugin status")
def on_plugin_status(src: CommandSource, ctx: CommandContext):
    """查看插件下载进程状态"""
    if not _console_only(src):
        return
    if rt.current_download is None:
        src.reply(RText("当前没有正在运行的插件下载进程", RColor.gray))
        return

    ds = rt.current_download
    ds.tick()
    info = RTextList(
        RText(f"URL: {ds.url}\n", RColor.gray),
        RText(f"已下载: {core.human_size(ds.downloaded_bytes)}", RColor.aqua),
    )
    if ds.total_bytes > 0:
        pct = ds.downloaded_bytes / ds.total_bytes * 100
        info.append(
            RText(
                f" / {core.human_size(ds.total_bytes)} ({pct:.1f}%)",
                RColor.gray,
            )
        )
    info.append(RText(f"\n速度: {core.human_size(ds.speed)}/s", RColor.aqua))
    if ds.eta is not None:
        info.append(RText(f"  剩余: {core.format_time(ds.eta)}", RColor.gray))
    info.append(RText("\n使用 !!pip cancel 可以取消下载", RColor.gray))
    src.reply(info)
