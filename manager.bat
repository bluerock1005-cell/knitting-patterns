@echo off
chcp 65001 >nul 2>&1

REM ─── 定位项目 .venv ───
set VENV_DIR=%~dp0.venv
set VENV_PY=%VENV_DIR%\Scripts\python.exe
set VENV_PYW=%VENV_DIR%\Scripts\pythonw.exe

REM ─── 首次运行：创建 venv 并安装依赖 ───
if not exist "%VENV_PY%" (
    echo 正在初始化 Python 虚拟环境...
    python -m venv "%VENV_DIR%"
    echo 正在安装依赖...
    "%VENV_PY%" -m pip install PyQt6 pypdf requests beautifulsoup4
    echo.
)

REM ─── 用 pythonw.exe 启动（无黑窗）───
start "" "%VENV_PYW%" "%~dp0manager.py"
