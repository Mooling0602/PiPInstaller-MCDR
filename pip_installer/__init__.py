import subprocess
import sys

from mcdreforged.api.all import *


builder = SimpleCommandBuilder()

def on_load(server: PluginServerInterface, prev_module):
    builder.arg('package', Text)
    builder.register(server)
    server.logger.info("PyPI安装器准备就绪！")

@builder.command('!!pip install <package>')
@builder.command('!!pipi <package>')
def on_install_pypi(src: CommandSource, ctx: CommandContext):
    if src.is_console:
        package = ctx['package']
        cmd = [
            sys.executable,
            '-m', 'pip', 'install',
            package
        ]
        subprocess.Popen(cmd).wait()
        src.reply("PyPI包安装指令执行完成！")
    else:
        src.reply(RText("请在控制台中运行此命令！", RColor.red))