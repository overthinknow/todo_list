@echo off
chcp 65001 >nul
title 创建桌面快捷方式
cd /d "%~dp0"

:: 检查启动脚本
if not exist "启动GitHub工具箱.bat" (
    echo ? 未找到 启动GitHub工具箱.bat，请确认在正确的目录运行。
    pause
    exit /b 1
)

:: 获取桌面路径
set "DESKTOP=%USERPROFILE%\Desktop"
set "SHORTCUT_NAME=GitHub工具箱"

:: 创建 VBS 脚本生成快捷方式
set "VBS_FILE=%TEMP%\create_shortcut.vbs"
(
    echo Set WshShell = WScript.CreateObject("WScript.Shell"^)
    echo Set Shortcut = WshShell.CreateShortcut("%DESKTOP%\%SHORTCUT_NAME%.lnk"^)
    echo Shortcut.TargetPath = "%~dp0启动GitHub工具箱.bat"
    echo Shortcut.WorkingDirectory = "%~dp0"
    echo Shortcut.Description = "GitHub 工具箱 - 一站式仓库管理"
    echo Shortcut.IconLocation = "%~dp0streamlit_env\Lib\site-packages\streamlit\static\favicon.png, 0"
    echo Shortcut.Save
    echo WScript.Echo "done"
) > "%VBS_FILE%"

cscript //nologo "%VBS_FILE%" >nul
del "%VBS_FILE%" 2>nul

:: 检查是否创建成功
if exist "%DESKTOP%\%SHORTCUT_NAME%.lnk" (
    echo ✅ 桌面快捷方式已创建！
    echo    名称: %SHORTCUT_NAME%
    echo    位置: %DESKTOP%\%SHORTCUT_NAME%.lnk
) else (
    echo ? 快捷方式创建失败，请手动发送到桌面：
    echo    右键 启动GitHub工具箱.bat → 发送到 → 桌面快捷方式
)

echo.
echo 📖 详细使用说明请参阅 README.md
echo.
pause
