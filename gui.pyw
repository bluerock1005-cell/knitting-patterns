"""gui.pyw - 双击启动编织图纸管理器"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent.resolve()
VENV_DIR = HERE / ".venv"
VENV_PY = VENV_DIR / "Scripts" / "python.exe"
VENV_PYW = VENV_DIR / "Scripts" / "pythonw.exe"


def main():
    # 第一步：确保虚拟环境存在
    if not VENV_PY.exists():
        subprocess.run(
            [sys.executable, "-m", "venv", str(VENV_DIR)],
            check=False,
        )
        subprocess.run(
            [str(VENV_PY), "-m", "pip", "install",
             "PyQt6", "pypdf", "requests", "beautifulsoup4"],
            check=False,
        )
        # 短暂弹窗提示初始化完成
        subprocess.run(
            ["msg", "*", "环境初始化完成，请重新双击 gui.pyw"],
            check=False, timeout=3,
        )

    # 第二步：如果当前不是 venv 的 pythonw，用 venv 重新启动
    if VENV_PYW.exists() and str(sys.executable).lower() != str(VENV_PYW).lower():
        subprocess.Popen([str(VENV_PYW), __file__])
        return

    # 第三步：启动管理器
    sys.path.insert(0, str(HERE))
    from PyQt6.QtWidgets import QApplication
    from manager import PatternManager

    HERE.mkdir(exist_ok=True)

    app = QApplication(sys.argv)
    app.setApplicationName("编织图纸管理器")
    window = PatternManager()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
