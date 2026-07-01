@echo off
chcp 65001 >nul 2>&1
title 编织图纸管理器

REM ─── 定位项目 .venv ───
set VENV_DIR=%~dp0.venv
set VENV_PY=%VENV_DIR%\Scripts\python.exe

REM ─── 首次运行：创建 venv 并安装依赖 ───
if not exist "%VENV_PY%" (
    echo 正在初始化 Python 虚拟环境...
    python -m venv "%VENV_DIR%"
    echo 正在安装依赖...
    "%VENV_PY%" -m pip install PyQt6 pypdf requests beautifulsoup4
    echo.
)

echo 正在启动编织图纸管理器...
"%VENV_PY%" "%~dp0manager.py"
if %errorlevel% neq 0 (
    echo.
    echo *** 启动失败 ***
    echo 请检查错误信息，或手动运行: pip install PyQt6 pypdf requests beautifulsoup4
    pause
)
