from __future__ import annotations

from .models import SystemCommand


class WindowsSystemCommandProvider:
    def commands(self) -> list[SystemCommand]:
        return [
            SystemCommand(
                id="this-pc",
                name="此电脑",
                icon="qta:mdi6.laptop",
                description="打开资源管理器",
                action="explorer.exe",
                keywords=["电脑", "computer", "我的电脑"],
            ),
            SystemCommand(
                id="control-panel",
                name="控制面板",
                icon="qta:mdi6.cog",
                description="打开控制面板",
                action="control.exe",
                keywords=["控制", "panel", "设置"],
            ),
            SystemCommand(
                id="cmd",
                name="命令提示符",
                icon="qta:mdi6.console",
                description="打开命令行",
                action="cmd.exe",
                keywords=["cmd", "命令行", "终端", "terminal", "shell"],
            ),
            SystemCommand(
                id="taskmgr",
                name="任务管理器",
                icon="qta:mdi6.chart-bar",
                description="打开任务管理器",
                action="taskmgr.exe",
                keywords=["任务", "task", "进程", "performance"],
            ),
            SystemCommand(
                id="notepad",
                name="记事本",
                icon="qta:mdi6.file-document-outline",
                description="打开记事本",
                action="notepad.exe",
                keywords=["note", "文本", "text", "编辑"],
            ),
            SystemCommand(
                id="calc",
                name="计算器",
                icon="qta:mdi6.calculator",
                description="打开计算器",
                action="calc.exe",
                keywords=["calc", "计算", "math"],
            ),
            SystemCommand(
                id="restart-app",
                name="重启应用",
                icon="qta:mdi6.restart",
                description="快速重启桌面工具箱",
                action="__restart_app__",
                keywords=["restart", "reload", "重启", "刷新", "应用", "app"],
            ),
        ]


class MacOSSystemCommandProvider:
    def commands(self) -> list[SystemCommand]:
        return [
            SystemCommand(
                id="finder",
                name="Finder",
                icon="qta:mdi6.folder",
                description="打开 Finder",
                action="open -a Finder",
                keywords=["finder", "文件", "file", "文件管理器"],
            ),
            SystemCommand(
                id="system-settings",
                name="系统设置",
                icon="qta:mdi6.cog",
                description="打开系统设置",
                action='open -a "System Settings"',
                keywords=["设置", "settings", "system"],
            ),
            SystemCommand(
                id="terminal",
                name="终端",
                icon="qta:mdi6.console",
                description="打开终端",
                action="open -a Terminal",
                keywords=["terminal", "shell", "终端"],
            ),
            SystemCommand(
                id="activity-monitor",
                name="活动监视器",
                icon="qta:mdi6.chart-bar",
                description="打开活动监视器",
                action='open -a "Activity Monitor"',
                keywords=["activity", "monitor", "进程", "性能"],
            ),
            SystemCommand(
                id="calculator",
                name="计算器",
                icon="qta:mdi6.calculator",
                description="打开计算器",
                action="open -a Calculator",
                keywords=["calc", "计算", "math"],
            ),
            SystemCommand(
                id="restart-app",
                name="重启应用",
                icon="qta:mdi6.restart",
                description="快速重启桌面工具箱",
                action="__restart_app__",
                keywords=["restart", "reload", "重启", "刷新", "应用", "app"],
            ),
        ]


class NoopSystemCommandProvider:
    def commands(self) -> list[SystemCommand]:
        return [
            SystemCommand(
                id="restart-app",
                name="重启应用",
                icon="qta:mdi6.restart",
                description="快速重启桌面工具箱",
                action="__restart_app__",
                keywords=["restart", "reload", "重启", "刷新", "应用", "app"],
            )
        ]
