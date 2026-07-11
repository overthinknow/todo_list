@echo off
setlocal enabledelayedexpansion

:: ==================== 配置区 ====================
set "REPO_DIR=C:\Users\qwe\Desktop\111\todo_list"   :: 本地仓库路径
set "BRANCH=main"                                   :: 分支名
set "GITHUB_REPO=overthinknow/todo_list"            :: 远程仓库（用于打开页面）
set "DELETE_LOCAL_COPY=1"                           :: 1=上传后自动删除本地副本, 0=保留
:: ================================================

:: 检查拖放
if "%~1"=="" (
    echo ?? 请把文件或文件夹拖放到此图标上，不要直接双击。
    pause
    exit /b 1
)

:: 检查本地仓库
if not exist "%REPO_DIR%\.git" (
    echo ? 错误：%REPO_DIR% 不是一个有效的 Git 仓库。
    echo 请先运行: gh repo clone overthinknow/todo_list "%REPO_DIR%"
    pause
    exit /b 1
)

:: 临时记录文件（用于清理）
set "LIST_FILE=%TEMP%\upload_items_%RANDOM%.txt"
if exist "%LIST_FILE%" del "%LIST_FILE%"

:: 复制所有拖入项
echo 正在复制文件...
set "ITEM_COUNT=0"
for %%I in (%*) do (
    set "CUR_PATH=%%~I"
    if not exist "!CUR_PATH!" (
        echo ?? 跳过不存在的项目: !CUR_PATH!
        continue
    )
    set "IS_DIR=0"
    if exist "!CUR_PATH!\*" set "IS_DIR=1"
    for %%F in ("!CUR_PATH!") do set "ITEM_NAME=%%~nxF"

    if !IS_DIR!==1 (
        echo 复制文件夹: !ITEM_NAME!
        xcopy "!CUR_PATH!" "%REPO_DIR%\!ITEM_NAME!\" /E /I /Y /Q >nul
        if errorlevel 1 (
            echo ? 复制文件夹 "!CUR_PATH!" 失败。
            del "%LIST_FILE%" 2>nul
            pause
            exit /b 1
        )
    ) else (
        echo 复制文件: !ITEM_NAME!
        copy /y "!CUR_PATH!" "%REPO_DIR%\" >nul
        if errorlevel 1 (
            echo ? 复制文件 "!CUR_PATH!" 失败。
            del "%LIST_FILE%" 2>nul
            pause
            exit /b 1
        )
    )
    echo !ITEM_NAME!>>"%LIST_FILE%"
    set /a ITEM_COUNT+=1
)

if %ITEM_COUNT%==0 (
    echo ? 没有成功复制任何文件，操作终止。
    del "%LIST_FILE%" 2>nul
    pause
    exit /b 1
)
echo ? 已复制 %ITEM_COUNT% 个项目到本地仓库。

:: 进入仓库
pushd "%REPO_DIR%"

:: 检查是否有实际变更
git status --porcelain | findstr /R "." >nul
if errorlevel 1 (
    echo ?? 所有文件已存在于仓库且内容相同，无需重复提交。
    if %DELETE_LOCAL_COPY%==1 call :cleanup
    popd
    goto :success
)

:: 提交
git add .
git commit -m "Batch upload multiple files" >nul 2>&1
if errorlevel 1 (
    echo ? Git 提交失败，请检查仓库状态。
    if %DELETE_LOCAL_COPY%==1 call :cleanup
    popd
    pause
    exit /b 1
)
echo ? 本地提交成功。

:: 推送（带重试）
echo 正在推送至 GitHub...
set RETRY=0
:push_loop
git push origin %BRANCH% 2>&1 | findstr /C:"error" >nul
if not errorlevel 1 (
    if %RETRY% lss 2 (
        echo ?? 推送遇到问题，正在重试（%RETRY%/2）...
        set /a RETRY+=1
        pause
        goto push_loop
    ) else (
        echo ? 推送失败！请手动检查仓库。
        if %DELETE_LOCAL_COPY%==1 call :cleanup
        popd
        pause
        exit /b 1
    )
)
echo ? 推送成功。

:: 清理本地副本
if %DELETE_LOCAL_COPY%==1 call :cleanup

popd

:success
:: 打开仓库页面
start "" "https://github.com/%GITHUB_REPO%"
echo.
echo ? 操作完成！窗口将在 3 秒后自动关闭...
timeout /t 3 >nul
exit /b 0


:: ========== 清理子程序 ==========
:cleanup
echo 正在清理本地副本...
if not exist "%LIST_FILE%" (
    echo 清理列表丢失，无法自动清理。
    goto :eof
)
for /f "usebackq delims=" %%i in ("%LIST_FILE%") do (
    set "ITEM=%%i"
    if exist "%REPO_DIR%\!ITEM!\*" (
        rmdir /s /q "%REPO_DIR%\!ITEM!" 2>nul
    ) else (
        del "%REPO_DIR%\!ITEM!" /q 2>nul
    )
    git checkout -- "!ITEM!" >nul 2>&1
    if errorlevel 1 git clean -fd "!ITEM!" >nul 2>&1
)
del "%LIST_FILE%" 2>nul
echo ?? 本地副本已清理。
goto :eof