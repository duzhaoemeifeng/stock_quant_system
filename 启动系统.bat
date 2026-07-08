@echo off
chcp 65001 >nul
title 股票量化交易系统

echo ========================================
echo   股票量化交易系统
echo   BaiStock 真实数据 + AI Agent
echo ========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 请先安装 Python 3.10+: https://python.org
    pause
    exit /b
)

echo ✅ Python 已就绪

:: Install deps (first time only)
if not exist ".deps_installed" (
    echo.
    echo 📦 安装依赖包（首次运行，需1-2分钟）...
    pip install -r requirements.txt -q
    if errorlevel 1 (
        echo ❌ 安装失败，请检查网络后重试
        pause
        exit /b
    )
    echo ✅ 依赖安装完成 > ".deps_installed"
    echo ✅ 安装完成
)

echo.
echo 🚀 启动系统中...
echo    浏览器将自动打开 http://localhost:8501
echo.
echo ⚠️ 勾选侧边栏「使用实盘数据」获取真实行情
echo    支持 BaoStock 数据源（免注册，免 API Key）
echo.
timeout /t 2 >nul
start http://localhost:8501
streamlit run app.py --server.headless false

pause
