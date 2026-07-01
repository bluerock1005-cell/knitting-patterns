@echo off
chcp 65001 >nul 2>&1

set VENV_DIR=%~dp0.venv
set VENV_PY=%VENV_DIR%\Scripts\python.exe
set VENV_PYW=%VENV_DIR%\Scripts\pythonw.exe

if not exist "%VENV_PY%" (
    echo 正在初始化 Python 环境...
    python -m venv "%VENV_DIR%"
    echo 正在安装依赖...
    "%VENV_PY%" -m pip install PyQt6 pypdf requests beautifulsoup4
    echo 初始化完成，请重新双击启动
    pause
    exit
)

start "" "%VENV_PYW%" "%~dp0manager.py"
