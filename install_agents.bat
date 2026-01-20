@echo off
echo Installing openai-agents... > install_batch.log
d:\todo_phase1\backend\.venv\Scripts\pip install openai-agents >> install_batch.log 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Installation failed with error code %ERRORLEVEL% >> install_batch.log
) else (
    echo Installation succeeded >> install_batch.log
)
type install_batch.log
