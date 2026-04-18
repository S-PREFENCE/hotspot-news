@echo off
chcp 65001 >nul
title 每日热点 - 后台服务
cd /d "D:\A-ai自动化\hotspot_news"

:::: 清理Python缓存
for /d /r %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" 2>nul

:::: 检查端口是否已占用，如果已占用则跳过启动
netstat -ano | findstr ":5000 " | findstr "LISTENING" >nul 2>&1
if %errorlevel%==0 (
    echo 服务已在运行中，直接打开浏览器...
) else (
    echo 正在启动热点服务...
    start /b python app.py > nul 2>&1
    timeout /t 2 /nobreak > nul
)

:::: 打开浏览器
start http://localhost:5000
exit
