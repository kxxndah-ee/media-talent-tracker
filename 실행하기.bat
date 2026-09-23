@echo off
chcp 65001 > nul
echo ==============================================
echo  언론사 인사이동 트래커 앱을 실행하고 있습니다...
echo  이전 세션 정리 및 브라우저 실행 중...
echo ==============================================

:: 8501 포트를 점유하고 있던 이전 프로세스가 있다면 자동 종료
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8501 ^| findstr LISTENING') do taskkill /f /pid %%a >nul 2>&1

cd /d "%~dp0"
uv run streamlit run run.py --server.port 8501 --browser.gatherUsageStats false
pause
