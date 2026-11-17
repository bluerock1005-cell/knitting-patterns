@echo off
chcp 65001 >nul 2>&1
setlocal
pushd "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo 请先运行 manager.py，完成虚拟环境和依赖安装。
    popd
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo 请先安装打包工具，再重新运行本脚本。
    echo .venv\Scripts\python.exe -m pip install pyinstaller
    popd
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m PyInstaller --noconfirm --onefile --windowed --name "编织图纸管理器" --distpath dist --workpath build --specpath build manager.py
if errorlevel 1 (
    echo 打包失败，请查看上方错误信息。
    popd
    pause
    exit /b 1
)

echo.
echo 已生成 dist\编织图纸管理器.exe
echo 在本项目内运行该文件，会自动使用项目根目录的 patterns.csv 和 docs。
echo 移动程序时，请将 exe 放在图纸库的 patterns.csv 旁边。
echo 推送 GitHub 需要该图纸库是已配置 origin 的 Git 仓库，并已安装 Git。
popd
pause
