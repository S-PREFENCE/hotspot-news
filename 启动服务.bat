@echo off
chcp 65001 >nul
title 每日热点 · 启动中...
cd /d "D:\A-ai自动化\hotspot_news"

echo ================================================
echo   每日热点网页服务
echo ================================================
echo.
echo [正在启动服务，请稍候...]
echo.

python app.py

pause
