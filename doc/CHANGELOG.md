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

## 0.3.0-rc4

> 预览测试版本，不会同步至插件仓库。

- 将命令模块中的核心逻辑进一步整合至`core.py`模块，避免受命令上下文干扰

**#full_changelog**

## 0.3.0-rc5

> 预览测试版本，不会同步至插件仓库。

- 修复取消插件下载后后台下载仍可能继续进行的问题
- 将MCDReforged最低版本要求调整为2.10.0，以匹配当前命令注册实现

**#full_changelog**

## 0.3.0

**最新变更**

- 优化插件依赖库的版本限制
- 改善加载消息的表述

**Compare last version**: https://github.com/Mooling0602/PiPInstaller-MCDR/compare/0.3.0-rc5...0.3.0

**预览版本变更汇总**

- 重构代码结构，更新项目文档
- 修复多个代码问题，改善插件的使用体验
- 新增依赖补全和快速安装远程第三方插件的功能
> 此功能并不能替代MCDReforged的插件管理器（PIM），仅适用于开发调试

- 新增必需的Python(PyPI)包依赖`requests>=2.32.5`以运行插件包下载功能

**Full changelog**: https://github.com/Mooling0602/PiPInstaller-MCDR/compare/0.2.3...0.3.0