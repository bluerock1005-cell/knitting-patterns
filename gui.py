"""gui.py - 双击或命令行启动编织图纸管理器"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent.resolve()
VENV_DIR = HERE / ".venv"
VENV_PY = VENV_DIR / "Scripts" / "python.exe"


def main():
    # 第一步：确保虚拟环境存在
    if not VENV_PY.exists():
        print("正在创建虚拟环境，首次运行需要1-2分钟…")
        subprocess.run(
            [sys.executable, "-m", "venv", str(VENV_DIR)],
            check=True,
        )
        subprocess.run(
            [str(VENV_PY), "-m", "pip", "install",
             "PyQt6", "pypdf", "requests", "beautifulsoup4"],
            check=True,
        )
        print("初始化完成！请重新运行 gui.py")
        return

    # 第二步：用 venv 的 python 重新启动自己（如果不是已经在 venv 里）
    if str(sys.executable).lower() != str(VENV_PY).lower():
        subprocess.Popen([str(VENV_PY), __file__])
        return

    # 第三步：启动管理器
    sys.path.insert(0, str(HERE))
    from PyQt6.QtWidgets import QApplication
    from manager import PatternManager

    app = QApplication(sys.argv)
    app.setApplicationName("编织图纸管理器")
    window = PatternManager()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
