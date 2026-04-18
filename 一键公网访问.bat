@echo off
chcp 65001 >nul
title PrenceYours 2026 · 一键公网访问

echo ============================================
echo    PrenceYours 2026 · 一键公网访问
echo ============================================
echo.

cd /d "D:\A-ai自动化\hotspot_news"

::: 检查Flask服务是否已在运行
netstat -ano | findstr ":5000 " | findstr "LISTENING" >nul 2>&1
if %errorlevel%==0 (
    echo [√] Flask 服务已在运行
) else (
    echo [*] 正在启动 Flask 服务...
    start /B pythonw app.py
    timeout /t 3 >nul
    netstat -ano | findstr ":5000 " | findstr "LISTENING" >nul 2>&1
    if %errorlevel%==0 (
        echo [√] Flask 服务启动成功
    ) else (
        echo [×] Flask 服务启动失败
        pause
        exit /b 1
    )
)

::: 启动 cloudflared 隧道（使用http2协议，兼容性更好）
echo.
echo [*] 正在启动内网穿透隧道...
echo [*] 等待生成公网链接（约15秒）...
echo.

start /B cloudflared.exe tunnel --protocol http2 --url http://localhost:5000 2>"%TEMP%\cloudflared_log.txt"

::: 等待链接生成
timeout /t 15 >nul

::: 从日志中提取公网链接
findstr "trycloudflare.com" "%TEMP%\cloudflared_log.txt" >nul 2>&1
if %errorlevel%==0 (
    echo ============================================
    echo    公网链接生成成功！
    echo ============================================
    echo.
    for /f "tokens=6 delims=| " %%a in ('findstr "trycloudflare.com" "%TEMP%\cloudflared_log.txt"') do (
        echo    手机微信访问: %%a
    )
    echo.
    echo ============================================
    echo    提示：
    echo    - 链接可直接在微信中点击打开
    echo    - 电脑也可以直接访问
    echo    - 关闭此窗口将断开公网连接
    echo    - 每次重启会生成新链接
    echo    - 固定链接请参考 域名绑定说明.md
    echo ============================================
) else (
    echo.
    echo [!] 正在获取链接，请稍候...
    echo     如果长时间没有显示，可能是网络环境限制了隧道连接
    echo     请尝试：
    echo     1. 关闭VPN/代理后重试
    echo     2. 使用手机热点网络重试
    echo     3. 查看日志：%TEMP%\cloudflared_log.txt
)

echo.
echo 按任意键在浏览器中打开本地页面...
pause >nul
start http://localhost:5000
