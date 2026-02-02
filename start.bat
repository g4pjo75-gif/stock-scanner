@echo off
chcp 65001 >nul
title 글로벌 이평선 대순환 스캐너

echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║     글로벌 이평선 대순환 ^& 모멘텀 스캐너 (JP/US)        ║
echo ╚════════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: Python 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo Python 3.8 이상을 설치해주세요.
    pause
    exit /b 1
)

:: 가상환경 확인 및 생성
if not exist "venv" (
    echo [설정] 가상환경 생성 중...
    python -m venv venv
)

:: 가상환경 활성화
echo [설정] 가상환경 활성화...
call venv\Scripts\activate

:: 의존성 설치
if not exist "venv\.installed" (
    echo [설정] 패키지 설치 중 (최초 1회)...
    pip install -r backend\requirements.txt
    echo. > venv\.installed
)

:: 데이터 폴더 생성
if not exist "data" mkdir data

echo.
echo [시작] 서버를 시작합니다...
echo [접속] http://localhost:8000
echo [종료] Ctrl+C
echo.

:: 서버 실행
cd backend
python main.py
