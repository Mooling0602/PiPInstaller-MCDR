import subprocess
import sys
from typing import Any, Optional

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

# 全局变量存储当前安装进程
current_process: Optional[subprocess.Popen] = None


def on_load(server: PluginServerInterface, prev_module: Any):
    builder.arg("package", GreedyText)
    builder.register(server)
    server.logger.info("PyPI安装器已加载！")


@builder.command("!!pip install <package>")
@builder.command("!!pipi <package>")
@new_thread("PiPInstaller:Install")
def on_install_pypi(src: CommandSource, ctx: CommandContext):
    global current_process

    if not src.is_console:
        src.reply(RText("请在控制台中运行此命令！", RColor.red))
        return

    # 检查是否已有安装进程在运行
    if current_process is not None and current_process.poll() is None:
        src.reply(
            RText(
                "已有安装进程在运行中，请等待完成或使用 !!pip cancel 取消！",
                RColor.yellow,
            )
        )
        return

    packages: list[str] = ctx["package"].split()

    # 检查是否包含 -q 选项
    quiet_mode = "-q" in packages
    if quiet_mode:
        packages.remove("-q")  # 移除 -q 选项，不传递给pip

    src.reply(RText(f"开始安装包: {', '.join(packages)}", RColor.aqua))

    try:
        cmd: list[str] = [sys.executable, "-m", "pip", "install", *packages]

        if quiet_mode:
            # 静默模式：捕获输出，安装完成后显示
            current_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )

            # 等待进程完成
            stdout, stderr = current_process.communicate()

            if current_process.returncode == 0:
                src.reply(RText("PyPI包安装完成！", RColor.green))
                if stdout:
                    src.reply(f"输出: {stdout}")
            else:
                src.reply(RText("PyPI包安装失败！", RColor.red))
                if stderr:
                    src.reply(f"错误: {stderr}")
        else:
            # 实时模式：直接显示输出
            current_process = subprocess.Popen(cmd)

            # 等待进程完成
            current_process.wait()

            if current_process.returncode == 0:
                src.reply(RText("PyPI包安装完成！", RColor.green))
            else:
                src.reply(RText("PyPI包安装失败！", RColor.red))

    except Exception as e:
        src.reply(RText(f"安装过程中发生错误: {str(e)}", RColor.red))
    finally:
        current_process = None


@builder.command("!!pip cancel")
@builder.command("!!pipc")
def on_cancel_install(src: CommandSource, ctx: CommandContext):
    """取消当前正在进行的安装"""
    global current_process

    if not src.is_console:
        src.reply(RText("请在控制台中运行此命令！", RColor.red))
        return

    if current_process is None or current_process.poll() is not None:
        src.reply(RText("当前没有正在运行的安装进程！", RColor.yellow))
        return

    try:
        # 终止进程
        current_process.terminate()

        # 等待进程结束，最多等待5秒
        try:
            current_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # 如果进程没有在5秒内结束，强制杀死
            current_process.kill()
            current_process.wait()

        src.reply(RText("安装进程已成功取消！", RColor.green))

    except Exception as e:
        src.reply(RText(f"取消安装时发生错误: {str(e)}", RColor.red))
    finally:
        current_process = None


@builder.command("!!pip status")
@builder.command("!!pips")
def on_install_status(src: CommandSource, ctx: CommandContext):
    """查看当前安装状态"""
    global current_process

    if not src.is_console:
        src.reply(RText("请在控制台中运行此命令！", RColor.red))
        return

    if current_process is None:
        src.reply(RText("当前没有正在运行的安装进程", RColor.gray))
    elif current_process.poll() is None:
        src.reply(RText("安装进程正在运行中...", RColor.yellow))
        src.reply(RText("使用 !!pip cancel 可以取消安装", RColor.gray))
    else:
        # 进程已结束但还未清理
        return_code = current_process.returncode
        if return_code == 0:
            src.reply(RText("最近的安装进程已成功完成", RColor.green))
        else:
            src.reply(RText(f"最近的安装进程失败 (退出码: {return_code})", RColor.red))
