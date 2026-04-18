@echo off
chcp 65001 >nul
title PrenceYours 2026 - 固定域名公网访问

echo ============================================
echo   PrenceYours 2026 - 固定域名公网访问
echo ============================================
echo.

REM 检查 cloudflared 是否已登录
if not exist "%USERPROFILE%\.cloudflared\cert.pem" (
    echo [!] 未检测到 cloudflared 登录凭证
    echo [!] 请先运行 域名绑定说明.md 中的步骤完成登录
    echo.
    echo 正在打开登录页面...
    cloudflared.exe login
    if errorlevel 1 (
        echo [X] 登录失败，请重试
        pause
        exit /b 1
    )
)

REM 检查 tunnel 是否已创建
if not exist "%USERPROFILE%\.cloudflared\prenceyours2026.json" (
    echo [!] 未检测到 named tunnel 配置
    echo [!] 正在创建 tunnel...
    cloudflared.exe tunnel create prenceyours2026
    if errorlevel 1 (
        echo [X] Tunnel 创建失败，请检查是否已登录
        pause
        exit /b 1
    )
)

REM 清理 __pycache__
echo [*] 清理 __pycache__...
if exist "__pycache__" rd /s /q "__pycache__"
if exist "scraper\__pycache__" rd /s /q "scraper\__pycache__"
if exist "models\__pycache__" rd /s /q "models\__pycache__"

REM 启动 Flask 服务（后台）
echo [*] 启动 Flask 服务...
start /b python app.py

REM 等待 Flask 启动
timeout /t 5 /nobreak >nul

REM 启动 cloudflared named tunnel
echo [*] 启动固定域名隧道...
echo [*] 访问地址: https://prenceyours2026.com
echo.
echo ============================================
echo   服务已启动！按 Ctrl+C 停止
echo   公网地址: https://prenceyours2026.com
echo ============================================
echo.

cloudflared.exe tunnel --protocol http2 run prenceyours2026
