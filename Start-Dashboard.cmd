@echo off
setlocal
pushd "%~dp0" || exit /b 1
if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv. Follow docs\demo-readiness.md to install the environment.
  pause
  popd
  exit /b 1
)
".venv\Scripts\python.exe" tools\check_demo.py
if errorlevel 1 (
  echo Preflight failed. Resolve FAIL entries before demonstrating.
  pause
  popd
  exit /b 1
)
echo Open http://127.0.0.1:8765 in your browser. Keep this window open.
".venv\Scripts\python.exe" tools\run_dashboard.py
if errorlevel 1 pause
popd
endlocal
