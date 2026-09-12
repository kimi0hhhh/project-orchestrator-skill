@echo off
REM 看板服务 —— 后台启动器（无 pause，供 WMI / 计划任务等脱离调用者进程树的方式拉起）
REM
REM 为什么需要它：由受限 shell 直接启动的服务，会随该 shell 所在进程树的回收一起被杀，
REM 表现为"刚启动就连不上"。用 WMI (Win32_Process.Create) 或计划任务启动本脚本，
REM 服务的父进程变成 WmiPrvSE / TaskScheduler，不再受调用者进程树影响。
REM
REM 手动用：直接双击 start.cmd（带 pause，出错时能看清原因）。

cd /d "%~dp0.."
set PY=%USERPROFILE%\.workbuddy\binaries\python\versions\3.13.12\python.exe
if not exist "%PY%" set PY=python

"%PY%" runtime\board.py ensure >> runtime\board.log 2>&1
