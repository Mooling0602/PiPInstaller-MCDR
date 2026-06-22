from mcdreforged.api.all import PluginServerInterface
from pip_installer.commands import command_register
from pip_installer.config import register_command_aliases


def on_load(server: PluginServerInterface, _):
    command_register(server)
    register_command_aliases(server)
    server.logger.info("Python(PyPI)包安装器已加载！")
