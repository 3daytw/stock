@echo off
chcp 65001 >nul
echo.
echo  ╔══════════════════════════════════════╗
echo  ║    AI 概念股分析平台  啟動中...       ║
echo  ╚══════════════════════════════════════╝
echo.
cd /d "%~dp0backend"
echo [1/2] 安裝相依套件...
pip install -r requirements.txt -q
echo [2/2] 啟動伺服器 http://localhost:8000
echo.
echo  請在瀏覽器開啟：http://localhost:8000
echo  按 Ctrl+C 停止伺服器
echo.
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
