@echo off
chcp 65001 >nul
title 推送代码到 GitHub

echo ============================================
echo    每日热点 - 推送代码到 GitHub
echo ============================================
echo.

cd /d "D:\A-ai自动化\hotspot_news"

:: 检查 Git
"C:\Program Files\Git\bin\git.exe" --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Git，请先安装 Git
    pause
    exit /b 1
)

echo [1/3] 请输入你的 GitHub 用户名:
set /p GH_USER="用户名: "

echo.
echo [2/3] 请输入仓库名（直接回车使用 hotspot-news）:
set /p GH_REPO="仓库名: "
if "%GH_REPO%"=="" set GH_REPO=hotspot-news

echo.
echo ============================================
echo   重要：请先在 GitHub 上创建空仓库！
echo   打开 https://github.com/new
echo   仓库名填: %GH_REPO%
echo   选择 Public（公开）
echo   不要勾选 README / .gitignore / License
echo   点击 Create repository
echo ============================================
echo.
echo 完成后按任意键继续推送...
pause >nul

:: 添加远程仓库
"C:\Program Files\Git\bin\git.exe" remote remove origin >nul 2>&1
"C:\Program Files\Git\bin\git.exe" remote add origin https://github.com/%GH_USER%/%GH_REPO%.git

:: 推送
echo.
echo [3/3] 正在推送代码到 GitHub...
"C:\Program Files\Git\bin\git.exe" branch -M main
"C:\Program Files\Git\bin\git.exe" push -u origin main

if errorlevel 1 (
    echo.
    echo [提示] 如果弹出登录窗口，请输入你的 GitHub 账号密码
    echo        或使用 Personal Access Token 作为密码
    echo        Token 生成地址: https://github.com/settings/tokens
    echo.
    echo 推送失败，请检查用户名和仓库是否正确
    pause
    exit /b 1
)

echo.
echo ============================================
echo   推送成功！
echo   仓库地址: https://github.com/%GH_USER%/%GH_REPO%
echo.
echo   下一步：部署到 Render.com
echo   打开 https://dashboard.render.com/select-repo
echo   选择 %GH_REPO% 仓库
echo   Render 会自动检测配置并部署
echo ============================================
echo.
pause
