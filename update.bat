@echo off
chcp 65001 >nul 2>&1
title 编织图纸库 - 一键更新

echo ==========================================
echo   编织图纸库 - 一键更新脚本
echo ==========================================
echo.

REM ─── 第一步：重新生成网页 ───
echo [1/3] 正在重新生成网页...
"%~dp0.venv\Scripts\python.exe" generate_site.py
if %errorlevel% neq 0 (
    echo *** 生成网页失败，请检查 patterns.csv 格式 ***
    pause
    exit /b 1
)
echo.

REM ─── 第二步：Git 提交 ───
echo [2/3] 正在提交到 Git...
git add -A
git commit -m "更新图纸库 %date% %time%"
echo.

REM ─── 第三步：推送到 GitHub ───
echo [3/3] 正在推送到 GitHub...
git push origin main
if %errorlevel% neq 0 (
    echo.
    echo *** 推送失败！可能原因：***
    echo   1. 还没有初始化 git 仓库 → 运行: git init
    echo   2. 还没有关联远程仓库 → 运行: git remote add origin https://github.com/你的用户名/knitting-patterns.git
    echo   3. 首次推送需要: git push -u origin main
    echo.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo   ✅ 更新完成！
echo   网页将在几分钟后自动更新
echo ==========================================
pause
