@echo off
chcp 65001 >nul 2>&1
title 编织图纸管理器

REM ─── 定位 venv Python ───
set VENV_PY=C:\Users\chong elaine\.workbuddy\binaries\python\envs\default\Scripts\python.exe

if not exist "%VENV_PY%" (
    echo 正在初始化 Python 环境，首次运行需要安装依赖...
    C:\Users\"chong elaine"\.workbuddy\binaries\python\versions\3.13.12\python.exe -m venv "C:\Users\chong elaine\.workbuddy\binaries\python\envs\default"
    "%VENV_PY%" -m pip install PyQt6 pypdf
)

echo 正在启动编织图纸管理器...
"%VENV_PY%" "%~dp0manager.py"
if %errorlevel% neq 0 (
    echo.
    echo *** 启动失败 ***
    echo 请检查错误信息，或手动运行: pip install PyQt6 pypdf
    pause
)
