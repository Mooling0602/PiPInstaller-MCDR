# CHANGELOG
Changelog contents for parsing in CI.

## 0.2.3
该版本没有任何实际更新，仅对代码结构进行了重构。
> 此构建用于测试CI（自动发版）是否正常工作，可以选择不更新。

**#full_changelog**

## 0.3.0-rc1

> 预览测试版本，不会同步至插件仓库。

- 重构代码结构
- 更新项目文档信息
- 增加插件依赖识别补全功能
- 添加`!!plg_install <file_url>`命令用以快速安装远程插件文件

**Full changelog**: https://github.com/Mooling0602/PiPInstaller-MCDR/compare/0.2.3...0.3.0-rc1

## 0.3.0-rc2

> 预览测试版本，不会同步至插件仓库。

- 改用`pip`工具直接解析txt格式的Python(PyPI)包依赖列表
- 增强了插件包校验的健壮性

**#full_changelog**

## 0.3.0-rc3

> 预览测试版本，不会同步至插件仓库。

- 修复了插件下载线程中无法获取到`PluginServerInterface`上下文的问题

> `PluginServerInterface`是MCDReforged提供给插件的核心API实例。

**#full_changelog**