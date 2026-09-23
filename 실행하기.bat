@echo off
chcp 65001 > nul
echo ==============================================
echo  언론사 인사이동 트래커 앱을 실행하고 있습니다...
echo  브라우저 주소: http://localhost:8502
echo ==============================================

:: 8502 포트를 점유하고 있던 이전 프로세스가 있다면 자동 종료
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8502 ^| findstr LISTENING') do taskkill /f /pid %%a >nul 2>&1

cd /d "%~dp0"
uv run streamlit run app.py --server.port 8502 --browser.gatherUsageStats false
pause
