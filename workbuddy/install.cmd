@echo off
chcp 65001 >nul
setlocal

REM ============================================================
REM  多 Agent 协作体系 · 安装到目标工作区
REM  用法: install.cmd  <目标工作区路径>
REM  例:   install.cmd  C:\Users\me\WorkBuddy\my-project
REM  特性: 不覆盖已存在的同名文件（robocopy /XC /XN /XO）
REM ============================================================

set "SRC=%~dp0"
if "%~1"=="" (
    echo [!] 用法: install.cmd ^<目标工作区路径^>
    exit /b 1
)
set "DST=%~1"
if not exist "%DST%" mkdir "%DST%"

echo.
echo 源: %SRC%  (project-orchestrator v4.1 / WorkBuddy 版)
echo 目标: %DST%
echo.

call :copy_dir "%SRC%agents"          "%DST%\.workbuddy\agents"
call :copy_dir "%SRC%protocols"       "%DST%\.workbuddy\protocols"
call :copy_dir "%SRC%templates\state" "%DST%\.workbuddy\state"
call :copy_dir "%SRC%runtime"         "%DST%\runtime"
call :copy_dir "%SRC%docs"            "%DST%\docs"

echo --- 根目录文件 ---
for %%F in (ORCHESTRATOR.md README.md SKILL.md AGENTS.md) do (
    if exist "%DST%\%%F" (
        echo   跳过（已存在）: %%F
    ) else (
        copy "%SRC%%%F" "%DST%\%%F" >nul && echo   已复制: %%F
    )
)

echo.
echo ============================================================
echo  安装完成。下一步：
echo   1. 填  %DST%\docs\PROJECT_BRIEF.md  （必填四项）
echo   2. 起看板: python runtime\board.py wmi
echo   3. 告诉主 Agent: 「按 ORCHESTRATOR.md 跑 S1」
echo ============================================================
echo.
echo --- 移植完整性自检 ---
for %%F in (
    ".workbuddy\agents\00-orchestrator.md"
    ".workbuddy\agents\01-product-manager.md"
    ".workbuddy\agents\02-architect.md"
    ".workbuddy\agents\03-frontend-dev.md"
    ".workbuddy\agents\04-backend-dev.md"
    ".workbuddy\agents\05-dev-lead.md"
    ".workbuddy\agents\06-qa.md"
    ".workbuddy\protocols\gate-rules.md"
    ".workbuddy\protocols\handoff-schema.md"
    ".workbuddy\protocols\revision-loop.md"
    ".workbuddy\state\board.md"
    ".workbuddy\state\gate-log.md"
    ".workbuddy\state\open-issues.md"
    "runtime\cli.py"
    "runtime\server.py"
    "runtime\daemon.py"
    "runtime\board.py"
    "runtime\serve.cmd"
    "runtime\lib\store.py"
    "runtime\lib\contract.py"
    "runtime\registry.json"
    "ORCHESTRATOR.md"
) do (
    if exist "%DST%\%%~F" (
        echo   [ok]   %%~F
    ) else (
        echo   [MISS] %%~F
    )
)
where python >nul 2>nul
if not errorlevel 1 (
    pushd "%DST%"
    python runtime\cli.py --help >nul 2>nul
    if errorlevel 1 (
        echo   [WARN] cli.py --help 执行失败（检查 python 环境）
    ) else (
        echo   [ok]   cli.py --help 可用
    )
    python runtime\cli.py contracts >nul 2>nul
    if errorlevel 1 (
        echo   [WARN] cli.py contracts 执行失败（契约内联派发将不可用）
    ) else (
        echo   [ok]   cli.py contracts 可用
    )
    python runtime\cli.py dispatch --agent qa --check >nul 2>nul
    if errorlevel 1 (
        echo   [ok]   dispatch --check 正确拦下缺项
    ) else (
        echo   [WARN] dispatch --check 未拦住缺项（预期 exit 1）
    )
    popd
) else (
    echo   [SKIP] 未找到 python，跳过 cli.py 检查
)
exit /b 0

:copy_dir
if not exist "%~2" mkdir "%~2"
robocopy "%~1" "%~2" /E /XC /XN /XO /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 (
    echo   [x] 复制失败: %~1
) else (
    echo   [ok] %~2
)
exit /b 0
