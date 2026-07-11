@echo off
chcp 65001 >nul
title GitHub 工具箱 v2.0
cd /d "%~dp0"

:: ========== 环境检测 ==========
set "STREAMLIT_PYTHON=%~dp0streamlit_env\Scripts\python.exe"
set "APP_SCRIPT=%~dp0github工具箱_streamlit.py"
set "README=%~dp0README.md"

if not exist "%APP_SCRIPT%" (
    echo ? 错误：未找到主程序文件 github工具箱_streamlit.py
    pause
    exit /b 1
)

if not exist "%STREAMLIT_PYTHON%" (
    echo ? 未找到虚拟环境 streamlit_env，尝试使用系统 Python...
    set "STREAMLIT_PYTHON=python"
    where python >nul 2>&1
    if errorlevel 1 (
        echo ? 系统中未找到 Python，请先安装 Python 3.9+
        pause
        exit /b 1
    )
)

:: ========== 检测端口 ==========
set "PORT=8501"
:check_port
netstat -ano 2>nul | findstr ":%PORT% " >nul
if not errorlevel 1 (
    set /a PORT+=1
    goto check_port
)

:: ========== 启动 ==========
cls
echo ╔══════════════════════════════════════════════╗
echo ║         🧰  GitHub 工具箱  v2.0              ║
echo ║        一站式 GitHub 仓库管理工具              ║
echo ╚══════════════════════════════════════════════╝
echo.
echo  [ℹ]  正在启动应用...
echo  [🌐]  浏览器地址: http://localhost:%PORT%
echo  [📖]  用户指南:   %README%
echo.
echo  ⚡ 按 Ctrl+C 可停止服务器
echo  ⚡ 关闭此窗口也会关闭应用
echo.
echo  正在启动中，请稍候...

start "" "%STREAMLIT_PYTHON%" -m streamlit run "%APP_SCRIPT%" --server.headless true --server.port %PORT%

:: 等待并打开浏览器
timeout /t 5 >nul
echo.
echo ✅ 应用已启动！正在打开浏览器...
start "" "http://localhost:%PORT%"
echo.
echo ✅ 如果浏览器未自动打开，请手动访问:
echo    http://localhost:%PORT%
echo.
echo 📖 详细使用说明请参阅 README.md
echo.
pause
