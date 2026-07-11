@echo off
setlocal enabledelayedexpansion

:: ==================== 配置区（已按你的实际路径填好） ====================
set "REPO_DIR=C:\Users\qwe\Desktop\111\todo_list"   :: 你的本地仓库路径
set "BRANCH=main"                                   :: 你的默认分支（如为 master 请修改）
set "GITHUB_REPO=overthinknow/todo_list"            :: 用于远程校验
set "DELETE_LOCAL_COPY=1"                           :: 1=上传后自动删除本地副本, 0=保留
:: ======================================================================

:: 1. 检查是否有任何文件/文件夹拖入
if "%~1"=="" (
    echo ?? 请把文件或文件夹拖放到这个图标上，不要直接双击。
    pause
    exit /b 1
)

:: 检查目标仓库是否存在
if not exist "%REPO_DIR%\.git" (
    echo ? 错误：%REPO_DIR% 不是一个有效的 Git 仓库。
    echo 请先运行: gh repo clone overthinknow/todo_list "%REPO_DIR%"
    pause
    exit /b 1
)

:: 2. 准备临时记录文件（保存所有上传项的名称，用于清理和提交信息）
set "LIST_FILE=%TEMP%\upload_items_%RANDOM%.txt"
if exist "%LIST_FILE%" del "%LIST_FILE%"

:: 3. 遍历所有拖入的项目，逐个复制到本地仓库
echo 正在复制文件...
set "ITEM_COUNT=0"
for %%I in (%*) do (
    set "CUR_PATH=%%~I"
    if not exist "!CUR_PATH!" (
        echo ?? 跳过不存在的项目: !CUR_PATH!
        continue
    )
    :: 判断是文件还是文件夹
    set "IS_DIR=0"
    if exist "!CUR_PATH!\*" set "IS_DIR=1"
    for %%F in ("!CUR_PATH!") do set "ITEM_NAME=%%~nxF"

    if !IS_DIR!==1 (
        echo 复制文件夹: !ITEM_NAME!
        xcopy "!CUR_PATH!" "%REPO_DIR%\!ITEM_NAME!\" /E /I /Y /Q >nul
        if errorlevel 1 (
            echo ? 复制文件夹 "!CUR_PATH!" 失败，请检查权限。
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
    :: 记录项目名（用于后续清理）
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

:: 4. 进入仓库目录
pushd "%REPO_DIR%"

:: 5. 检查是否有变更
git status --porcelain | findstr /R "." >nul
if errorlevel 1 (
    echo ?? 没有检测到任何变更，可能文件已存在且内容相同。
    if %DELETE_LOCAL_COPY%==1 call :cleanup
    popd
    pause
    exit /b 0
)

:: 6. 提交
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

:: 7. 推送（带简单重试）
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
        echo ? 推送失败！可能原因：网络问题、远程仓库变更、权限不足。
        echo 请尝试在 "%REPO_DIR%" 内手动 git push。
        if %DELETE_LOCAL_COPY%==1 call :cleanup
        popd
        pause
        exit /b 1
    )
)
echo ? 推送成功。

:: 8. 远程校验（简化提示）
echo 正在校验远程状态...
start "" "https://github.com/%GITHUB_REPO%"
echo ? 推送完成，浏览器已打开仓库页面。

:: 9. 清理本地副本（如果开启）
if %DELETE_LOCAL_COPY%==1 call :cleanup

popd
echo.
echo ?? 全部完成！按任意键退出...
pause >nul
exit /b 0


:: ========== 内部子程序：清理本地副本 ==========
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
    :: 恢复 Git 索引状态
    git checkout -- "!ITEM!" >nul 2>&1
    if errorlevel 1 git clean -fd "!ITEM!" >nul 2>&1
)
del "%LIST_FILE%" 2>nul
echo ?? 本地副本已清理。
goto :eof