@echo off
echo 🏥 Checking service health...

set services=frontend:80 backend:8000 web-ui:8501 grafana:3000 prometheus:9090

for %%s in (%services%) do (
    for /f "tokens=1,2 delims=:" %%a in ("%%s") do (
        curl -f "http://localhost:%%b/health" >nul 2>&1 || curl -f "http://localhost:%%b" >nul 2>&1
        if !errorlevel! equ 0 (
            echo ✅ %%a is healthy
        ) else (
            echo ❌ %%a is not responding
        )
    )
)