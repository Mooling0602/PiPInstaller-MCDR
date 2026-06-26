import copy
import json
from pathlib import Path

from mcdreforged.api.all import PluginServerInterface

aliases_for_command = {
    "!!pipc": "!!pip cancel",
    "!!pips": "!!pip status",
    "!!plgi": "!!pipi plugin",
}
command_aliases_config = Path("config") / "command_aliases" / "config.json"


def _get_fixed_aliases_data(data: dict) -> dict:
    """用于删除错误的命令别名配置，
    接受一个命令别名的字典数据并返回剔除错误键值对后的正确数据，
    随时可能弃用。"""
    keys_to_remove: list = []
    for k, _ in data.items():
        for k_, _ in aliases_for_command.items():
            if k == k_:
                keys_to_remove.append(k)
    for key in keys_to_remove:
        data.pop(key)
    return data


def register_command_aliases(server: PluginServerInterface):
    if command_aliases_config.exists():
        server.logger.info(
            "检测到Command Aliases配置存在，正在尝试自动添加命令别名……"
        )
        with open(command_aliases_config, "r") as f:
            try:
                existing_data: dict = json.load(f)
            except Exception as e:
                server.logger.error(
                    f"读取Command Aliases插件配置时遇到错误: {e}"
                )
                server.logger.warning("将跳过命令别名注册操作。")
                return
    else:
        server.logger.info(
            "Command Aliases插件配置文件不存在，无法注册命令别名。"
        )
        return
    command_aliases_data: dict = _get_fixed_aliases_data(
        copy.deepcopy(existing_data)
    )
    command_aliases_data["alias"].update(aliases_for_command)
    if command_aliases_data != existing_data:
        with open(command_aliases_config, "w") as f:
            json.dump(command_aliases_data, f, indent=4)
    server.logger.info(
        "成功添加或更新命令别名！使用 !!pip usage 查看详细用法。"
    )
