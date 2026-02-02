"""
이평선 대순환 스캐너 - 실행 파일용 래퍼
서버 시작 + 브라우저 자동 오픈
"""
import os
import sys
import webbrowser
import threading
import time

# PyInstaller 환경에서 경로 설정
if getattr(sys, 'frozen', False):
    # EXE로 실행된 경우
    BASE_DIR = os.path.dirname(sys.executable)
    # PyInstaller가 압축을 푼 임시 폴더 경로 (프론트엔드 등 포함)
    BUNDLE_DIR = sys._MEIPASS
else:
    # 일반 Python으로 실행된 경우
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = BASE_DIR

# backend 경로 추가 (BUNDLE_DIR 내의 backend 사용)
sys.path.insert(0, os.path.join(BUNDLE_DIR, 'backend'))

# 데이터 폴더 생성
data_dir = os.path.join(BASE_DIR, 'data')
os.makedirs(data_dir, exist_ok=True)

def open_browser():
    """3초 후 브라우저 열기"""
    time.sleep(3)
    webbrowser.open('http://localhost:8000')

def main():
    import uvicorn
    from main import app
    
    print("=" * 50)
    print("  이평선 대순환 스캐너 시작")
    print("=" * 50)
    print(f"  서버 주소: http://localhost:8000")
    print(f"  데이터 폴더: {data_dir}")
    print("=" * 50)
    print("  종료하려면 이 창을 닫으세요")
    print("=" * 50)
    
    # 브라우저 자동 열기 (백그라운드)
    threading.Thread(target=open_browser, daemon=True).start()
    
    # 서버 시작
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

if __name__ == "__main__":
    main()
