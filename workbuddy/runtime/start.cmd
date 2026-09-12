@echo off
REM 多 Agent 运行时看板 —— 双击即启动并自动打开浏览器
REM 端口不写死：沿用 runtime\.port，被占则自动顺延
cd /d "%~dp0.."
set PY=%USERPROFILE%\.workbuddy\binaries\python\versions\3.13.12\python.exe
if not exist "%PY%" set PY=python
"%PY%" runtime\board.py open
if errorlevel 1 pause
