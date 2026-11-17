"""运行时路径解析：区分开发模式与 PyInstaller 打包后的 frozen 模式。

打包后优先使用 .exe 旁边的图纸库，也支持从项目的 dist 等子目录运行。
独立分发时，数据保存在 .exe 旁边，不会因临时目录被清理而丢失。
"""
import sys
from pathlib import Path


def app_dir():
    """查找 exe 同目录或上一级的现有图纸库，开发模式使用脚本目录。"""
    if getattr(sys, "_MEIPASS", None):
        executable_dir = Path(sys.executable).resolve().parent
        for directory in (executable_dir, executable_dir.parent):
            if (directory / "patterns.csv").is_file():
                return directory
        return executable_dir
    # 开发模式：本模块所在目录
    return Path(__file__).resolve().parent
