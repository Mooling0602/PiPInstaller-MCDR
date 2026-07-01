# 仓库指南

## 常用命令
- 使用 `uv sync --all-groups` 安装依赖；CI 的检查和打包使用 Python 3.9，发布流程使用 Python 3.11。
- 本地检查运行 `uv run ./check.py`；它依次执行 `ty check src`、`ruff check src`、`ruff format --check src`。
- `check.py` 在缺少 `ty` 或 `ruff` 时只打印警告并继续执行，所以不要在未确认工具已安装时信任“看起来干净”的结果。
- 在仓库根目录用 `uv run mcdreforged pack -i src` 构建插件包；如需比较产物，先删除根目录旧的 `*.mcdr`。

## 项目结构
- MCDR 插件元数据和发布版本号位于 `src/mcdreforged.plugin.json`；Hatch 也从这个文件读取 Python 包版本。
- 运行时代码在 `src/pip_installer/`：`__init__.py` 在 `on_load` 注册命令，`commands.py` 定义 MCDR 命令，`core.py` 处理 pip、压缩包和下载逻辑，`runtime.py` 保存全局进程/下载状态，`config.py` 在检测到 Command Aliases 配置时修改别名。
- 面向用户的命令文档在 `README.md` 和 `USAGE.md`，且当前项目没有 I18n 计划；改动命令行为时更新中文文档，不要为此引入多语言结构。

## 插件行为
- 命令预期只在 MCDR 控制台执行；处理函数通过 `_console_only` 拒绝非控制台来源。
- `pip_installer.runtime` 全局只跟踪一个 pip 安装进程和一个插件下载状态；不要写成按用户或并发任务隔离的逻辑。
- 插件包格式限制为 `VALID_PLUGIN_PACKAGE_FORMATS = ["mcdr", "pyz", "zip"]`；依赖提取只查找压缩包根目录的精确文件名 `requirements.txt`。
- `!!pipi plugin <file_url>` 会把插件复制/移动到 `plugins/`，远程下载经过 `.cache/`，随后通过执行 `!!pip install -r <plugin_path>` 触发依赖安装。

## 风格与发布
- Ruff 目前只配置了 `line-length = 79`；除非 `pyproject.toml` 新增规则，否则不要假设存在更多 lint 约束。
- CI 只在推送到 `main` 且提交标题匹配 `feat:`/`fix:`、包含 `[#build_this]`，或符合发布提交/标签组合时运行。
- 发布标签不带前缀 `v`，并且必须指向标题为 `release: v<tag>` 的提交；发布说明从 `doc/CHANGELOG.md` 中匹配的 `## <tag>` 小节解析。
