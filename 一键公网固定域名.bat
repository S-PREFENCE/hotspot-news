@echo off
chcp 65001 >nul
title PrenceYours 2026 - 固定域名公网访问

echo ============================================
echo   PrenceYours 2026 - 固定域名公网访问
echo   (ClouDNS 免费域名 + Cloudflare Tunnel)
echo ============================================
echo.

REM ── 配置区域（按实际情况修改） ──
set TUNNEL_NAME=hotspot
set DOMAIN=YOUR-DOMAIN
REM 例如: set DOMAIN=prenceyours.cloudns.cc
REM ──────────────────────────────────

REM 检查 cloudflared 是否已登录
if not exist "%USERPROFILE%\.cloudflared\cert.pem" (
    echo [!] 未检测到 cloudflared 登录凭证
    echo [!] 请先按 域名绑定说明.md 完成以下步骤：
    echo     1. 在 ClouDNS 申请免费域名
    echo     2. 将域名托管到 Cloudflare
    echo     3. 运行 cloudflared.exe login
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
if not exist "%USERPROFILE%\.cloudflared\%TUNNEL_NAME%.json" (
    echo [!] 未检测到 named tunnel 配置
    echo [!] 正在创建 tunnel [%TUNNEL_NAME%]...
    cloudflared.exe tunnel create %TUNNEL_NAME%
    if errorlevel 1 (
        echo [X] Tunnel 创建失败，请检查是否已登录
        pause
        exit /b 1
    )
)

REM 检查域名是否已配置
if "%DOMAIN%"=="YOUR-DOMAIN" (
    echo [!] 请先修改本文件顶部的 DOMAIN 变量
    echo [!] 例如: set DOMAIN=prenceyours.cloudns.cc
    echo.
    echo [!] 然后运行以下命令添加 DNS 路由：
    echo     cloudflared.exe tunnel route dns %TUNNEL_NAME% 你的域名
    echo.
    pause
    exit /b 1
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
echo [*] 访问地址: https://%DOMAIN%
echo.
echo ============================================
echo   服务已启动！按 Ctrl+C 停止
echo   公网地址: https://%DOMAIN%
echo ============================================
echo.

cloudflared.exe tunnel --protocol http2 run %TUNNEL_NAME%
