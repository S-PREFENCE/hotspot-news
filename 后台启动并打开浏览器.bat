@echo off
chcp 65001 >nul
title 每日热点 · 后台运行
cd /d "D:\A-ai自动化\hotspot_news"

echo 正在后台启动每日热点服务...
start /B pythonw app.py

timeout /t 2 >nul
echo 服务已在后台运行！
echo 请在浏览器打开: http://localhost:5000
echo.
start http://localhost:5000
