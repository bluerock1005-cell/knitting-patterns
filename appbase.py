"""运行时路径解析：区分开发模式与 PyInstaller 打包后的 frozen 模式。

打包成 .exe 后，数据文件（patterns.csv、docs/）一律放在 .exe 所在目录，
这样发给别人后，数据会持久保存在 exe 旁边，不会因临时目录被清理而丢失。
"""
import sys
from pathlib import Path


def app_dir():
    """返回「数据根目录」：打包后=.exe 所在目录；开发模式=脚本所在目录。

    用 sys._MEIPASS 判断打包状态：PyInstaller 对 onefile / onedir 都会设置它，
    比 sys.frozen 更可靠。打包后数据放在 .exe 同目录，才能持久保存。
    """
    if getattr(sys, "_MEIPASS", None):
        # 打包后：.exe 本身所在的目录（用户解压/放置的位置，可写、持久）
        return Path(sys.executable).resolve().parent
    # 开发模式：本模块所在目录
    return Path(__file__).resolve().parent
