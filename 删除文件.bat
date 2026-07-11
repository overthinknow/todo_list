@echo off
setlocal enabledelayedexpansion
title GitHub 文件管理器（输入 h 查看命令 · q 退出）

:: ==================== 配置 ====================
set "REPO_DIR=C:\Users\qwe\Desktop\111\todo_list"
set "BRANCH=main"
set "GITHUB_REPO=overthinknow/todo_list"
:: ============================================

:: 1. 检查仓库目录
if not exist "%REPO_DIR%\.git" (
    echo ? 未找到本地 Git 仓库：%REPO_DIR%
    echo 请先执行：gh repo clone %GITHUB_REPO% "%REPO_DIR%"
    pause
    exit /b 1
)

pushd "%REPO_DIR%" || (
    echo ? 无法进入仓库目录。
    pause
    exit /b 1
)

:: 2. 同步远程
echo 正在同步远程仓库...
git fetch origin %BRANCH% 2>nul
git checkout %BRANCH% >nul 2>&1
git pull origin %BRANCH% >nul 2>&1

:: 3. 交互式主循环
set "CURRENT_PATH="
call :browse_dir ""
echo.
echo 程序已退出，窗口可手动关闭。
pause
exit /b 0


:: ==================== 浏览目录子程序 ====================
:browse_dir
set "DIRPATH=%~1"
if "%DIRPATH%"=="" (set "DISPLAY_PATH=根目录") else (set "DISPLAY_PATH=%DIRPATH%")

:show_dir
echo.
echo =================================================
echo  当前位置：%DISPLAY_PATH%
echo =================================================

:: 获取当前目录下的子目录和文件
set "DIR_LIST=%TEMP%\dir_list_%RANDOM%.txt"
set "FILE_LIST=%TEMP%\file_list_%RANDOM%.txt"

dir /b /ad "%DIRPATH%" > "%DIR_LIST%" 2>nul
dir /b /a-d "%DIRPATH%" > "%FILE_LIST%" 2>nul

set "DIR_COUNT=0"
if exist "%DIR_LIST%" for /f %%a in ('type "%DIR_LIST%" ^| find /c /v ""') do set "DIR_COUNT=%%a"
set "FILE_COUNT=0"
if exist "%FILE_LIST%" for /f %%a in ('type "%FILE_LIST%" ^| find /c /v ""') do set "FILE_COUNT=%%a"

set /a TOTAL=%DIR_COUNT% + %FILE_COUNT%
if %TOTAL%==0 (
    echo （此目录为空）
    del "%DIR_LIST%" 2>nul
    del "%FILE_LIST%" 2>nul
    pause
    goto :return
)

:: 显示条目（目录在前，文件在后）
set "INDEX=0"
echo.
if %DIR_COUNT% gtr 0 (
    for /f "usebackq delims=" %%d in ("%DIR_LIST%") do (
        set /a INDEX+=1
        echo   !INDEX!. [文件夹] %%d
    )
)
if %FILE_COUNT% gtr 0 (
    for /f "usebackq delims=" %%f in ("%FILE_LIST%") do (
        set /a INDEX+=1
        echo   !INDEX!. %%f
    )
)

del "%DIR_LIST%" 2>nul
del "%FILE_LIST%" 2>nul

:: ---------- 命令提示区（醒目） ----------
echo.
echo ─────────── 可用命令 ───────────
echo   数字 = 选择文件或文件夹
echo   （选文件 → 直接删除）
echo   （选文件夹 → 浏览/删除子菜单）
if not "%DIRPATH%"=="" echo   0    = 返回上级目录
echo   h    = 命令详细说明
echo   q    = 退出程序
echo ─────────────────────────────────
echo.

set "CHOICE="
set /p CHOICE=请输入序号或命令： 

:: 处理命令
if /i "%CHOICE%"=="q" (
    popd
    echo 已退出。
    pause
    exit /b 0
)
if /i "%CHOICE%"=="h" (
    call :show_help
    pause
    goto :show_dir
)
if "%CHOICE%"=="0" (
    if not "%DIRPATH%"=="" goto :return
    echo ? 已在根目录，无法返回。
    pause
    goto :show_dir
)
if "%CHOICE%"=="" (
    echo ? 未输入。
    pause
    goto :show_dir
)

:: 验证数字
if %CHOICE% lss 1 (
    echo ? 无效序号。
    pause
    goto :show_dir
)
if %CHOICE% gtr %INDEX% (
    echo ? 无效序号。
    pause
    goto :show_dir
)

:: 重新获取列表以找到选中条目（保持顺序：目录、文件）
set "FOUND_TYPE="
set "FOUND_NAME="
set "FOUND_PATH="
set "LINE_NUM=0"

dir /b /ad "%DIRPATH%" > "%DIR_LIST%" 2>nul
dir /b /a-d "%DIRPATH%" > "%FILE_LIST%" 2>nul

for /f "usebackq delims=" %%d in ("%DIR_LIST%") do (
    set /a LINE_NUM+=1
    if !LINE_NUM! equ %CHOICE% (
        set "FOUND_TYPE=dir"
        set "FOUND_NAME=%%d"
        if "%DIRPATH%"=="" (set "FOUND_PATH=%%d") else (set "FOUND_PATH=%DIRPATH%\%%d")
    )
)
if not defined FOUND_TYPE (
    for /f "usebackq delims=" %%f in ("%FILE_LIST%") do (
        set /a LINE_NUM+=1
        if !LINE_NUM! equ %CHOICE% (
            set "FOUND_TYPE=file"
            set "FOUND_NAME=%%f"
            if "%DIRPATH%"=="" (set "FOUND_PATH=%%f") else (set "FOUND_PATH=%DIRPATH%\%%f")
        )
    )
)
del "%DIR_LIST%" 2>nul
del "%FILE_LIST%" 2>nul

:: ---------- 处理选中条目 ----------
if "%FOUND_TYPE%"=="file" goto :delete_file

:: 选中文件夹 → 子菜单
:folder_menu
echo.
echo ============================================
echo  你选中了文件夹：%FOUND_NAME%
echo ============================================
echo   1. 进入文件夹浏览
echo   2. 删除整个文件夹（危险）
echo   0. 返回
echo.
set /p FOLDER_CHOICE=请选择操作： 

if "%FOLDER_CHOICE%"=="1" (
    call :browse_dir "%FOUND_PATH%"
    goto :return
)
if "%FOLDER_CHOICE%"=="2" (
    goto :delete_folder
)
if "%FOLDER_CHOICE%"=="0" (
    goto :show_dir
)
echo ? 无效输入，返回。
pause
goto :show_dir


:: ==================== 删除文件 ====================
:delete_file
echo.
echo ============================================
echo  即将删除远程文件：
echo  %GITHUB_REPO% / %BRANCH% / %FOUND_PATH%
echo ============================================
set /p CONFIRM=?? 输入 Y 确认删除，其他键取消： 
if /i not "%CONFIRM%"=="Y" (
    echo 已取消。
    pause
    goto :show_dir
)

:: 校验本地文件
if not exist "%FOUND_PATH%" (
    echo ? 本地文件 "%FOUND_PATH%" 不存在，无法继续。
    pause
    goto :show_dir
)
echo ? 本地文件存在，执行删除...

git rm "%FOUND_PATH%" >nul 2>&1
if errorlevel 1 (
    if exist "%FOUND_PATH%" (
        echo ? 删除失败，文件可能被占用。
        pause
        goto :show_dir
    ) else (
        git rm --cached "%FOUND_PATH%" >nul 2>&1
        if errorlevel 1 (
            echo ? 从索引删除失败。
            pause
            goto :show_dir
        )
    )
)

goto :commit_push


:: ==================== 删除文件夹 ====================
:delete_folder
echo.
echo ============================================
echo  即将删除远程文件夹（含所有内容）：
echo  %GITHUB_REPO% / %BRANCH% / %FOUND_PATH%
echo ============================================
set /p CONFIRM=?? 输入 Y 确认删除（不可恢复），其他键取消： 
if /i not "%CONFIRM%"=="Y" (
    echo 已取消。
    pause
    goto :show_dir
)

if not exist "%FOUND_PATH%" (
    echo ? 本地文件夹 "%FOUND_PATH%" 不存在。
    pause
    goto :show_dir
)
echo ? 本地文件夹存在，执行删除...

git rm -r "%FOUND_PATH%" >nul 2>&1
if errorlevel 1 (
    echo ? 删除文件夹失败（可能被占用或权限不足）。
    pause
    goto :show_dir
)

goto :commit_push


:: ==================== 提交、推送、校验 ====================
:commit_push
git commit -m "Delete %FOUND_PATH%" >nul 2>&1
echo 正在推送至 GitHub...
git push origin %BRANCH% >nul 2>&1
if errorlevel 1 (
    echo ? 推送失败，请检查网络或权限。
    pause
    goto :show_dir
)
echo ? 推送成功。

:: 远程校验
echo 正在校验删除结果...
git fetch origin %BRANCH% >nul 2>&1
if "%FOUND_TYPE%"=="file" (
    git cat-file -e origin/%BRANCH%:"%FOUND_PATH%" 2>nul
    if errorlevel 1 (
        echo ? 校验通过：文件已成功删除！
    ) else (
        echo ?? 远程文件似乎仍存在，请稍后刷新页面确认。
    )
) else (
    git ls-tree origin/%BRANCH% "%FOUND_PATH%" 2>nul | findstr /R "." >nul
    if errorlevel 1 (
        echo ? 校验通过：文件夹已成功删除！
    ) else (
        echo ?? 远程文件夹可能仍存在，请稍后刷新页面确认。
    )
)

:: 打开仓库对应目录
start "" "https://github.com/%GITHUB_REPO%/tree/%BRANCH%/%DIRPATH%"
pause
goto :show_dir


:: ==================== 帮助信息 ====================
:show_help
echo.
echo ══════════════ 命令详细说明 ══════════════
echo  数字 1、2、3...  → 选择对应序号的文件或文件夹
echo    · 文件：直接进入删除确认流程
echo    · 文件夹：弹出子菜单，可选择：
echo      1. 进入浏览
echo      2. 删除整个文件夹（危险）
echo      0. 返回
echo.
echo   0  → 返回上一级目录（仅子目录有效）
echo   h  → 显示此帮助
echo   q  → 退出程序
echo.
echo  【提示】删除操作均需输入 Y 二次确认，
echo   推送失败时会自动暂停并显示原因。
echo ═══════════════════════════════════════════
echo.
goto :eof


:return
goto :eof