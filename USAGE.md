# 插件使用文档

即插件用法。

## 概述

PiPInstaller-MCDR 用于在 MCDR 控制台中安装 Python 依赖（PyPI 包）和（位于插件仓库外的）插件。

**大部分命令需在 MCDR 控制台中执行**，不支持在游戏客户端中使用。

***

## 帮助命令

| 命令             | 说明           |
| -------------- | ------------ |
| `!!pipi`       | 查看主帮助页面      |
| `!!pipi help`  | 同上           |
| `!!pipi usage` | 同上           |
| `!!pip`        | 查看 pip 子命令帮助 |
| `!!pip usage`  | 同上           |

***

## 安装 PyPI 包

### `!!pipi <package>` / `!!pip install <package>`

从 PyPI 安装 Python 依赖，多个包用空格分隔。

```bash
# 安装单个包
!!pipi requests

# 安装指定版本
!!pipi numpy==1.26.0

# 安装多个包
!!pip install pandas matplotlib

# 静默模式（-q），安装完成后统一显示输出
!!pipi pillow -q
```

**注意**：同一时间只允许一个安装进程运行。使用 `!!pip status` 查看状态，`!!pip cancel` 取消。

***

## 从插件包安装依赖

### `!!pipi -r <file>` / `!!pip install -r <file>`

读取插件包（`.mcdr` / `.pyz` / `.zip`）内的 `requirements.txt` 并安装其中声明的依赖。

```bash
# 安装 MyPlugin.mcdr 的依赖
!!pipi -r MyPlugin.mcdr
```

**流程**：

1. 读取插件包中的 `requirements.txt`
2. 调用 `!!pip install` 依次安装各依赖

***

## 安装插件

### `!!pipi plugin <file_url>`

从远程 URL 或本地路径安装插件，自动处理依赖。

```bash
# 从远程 URL 安装
!!pipi plugin https://example.com/MyPlugin.mcdr

# 指定下载后的文件名（适用于 URL 无法解析文件名时）
!!pipi plugin https://example.com/download -o MyPlugin.mcdr

# 从本地路径安装
!!pipi plugin /path/to/MyPlugin.mcdr
```

**流程**：

- **远程 URL**：下载到 `.cache/` → 移动到 `plugins/` → 安装依赖
- **本地路径**：若不在 `plugins/` 中则复制 → 安装依赖

**下载特性**：

- 支持断点续传
- 下载开始后报告一次下载速度和剩余时间，后续可使用 `!!pipi plugin status` 查看实时进度

***

## 进程管理

### `!!pip status`

查看当前 pip 安装进程的状态。

### `!!pipi plugin status`

查看当前插件下载进程的状态，包括 URL、下载进度、速度和预估剩余时间。

### `!!pip cancel`

取消当前正在运行的进程（pip 安装或插件下载）。
