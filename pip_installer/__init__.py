import subprocess
import sys

from typing import Any
from mcdreforged.api.all import (
    SimpleCommandBuilder,
    PluginServerInterface,
    CommandSource,
    CommandContext,
    GreedyText,
    RText,
    RColor,
    new_thread,
)

builder = SimpleCommandBuilder()


def on_load(server: PluginServerInterface, prev_module: Any):
    builder.arg("package", GreedyText)
    builder.register(server)
    server.logger.info("PyPI安装器已加载！")


@builder.command("!!pip install <package>")
@builder.command("!!pipi <package>")
@new_thread("PiPInstaller:Main")
def on_install_pypi(src: CommandSource, ctx: CommandContext):
    if src.is_console:
        packages: list[str] = ctx["package"].split()
        cmd: list[str] = [sys.executable, "-m", "pip", "install", *packages]
        subprocess.Popen(cmd).wait()
        src.reply("PyPI包安装指令执行完成！")
    else:
        src.reply(RText("请在控制台中运行此命令！", RColor.red))
