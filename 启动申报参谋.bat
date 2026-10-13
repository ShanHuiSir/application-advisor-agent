@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  py -3 -m venv .venv
  if errorlevel 1 goto error
  .venv\Scripts\python.exe -m pip install -r requirements.txt
  if errorlevel 1 goto error
)
.venv\Scripts\python.exe desktop.py
if errorlevel 1 goto error
exit /b
:error
echo 启动失败。请先安装 Python 3.11 或更新版本，并确认网络可安装依赖。
pause
