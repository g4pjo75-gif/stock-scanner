
import sys
import os
import traceback

# 현재 파일(api/index.py)의 상위 상위 디렉토리(루트)를 path에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from backend.main import app
except Exception as e:
    # Import 실패 시 에러 내용을 보여주는 임시 앱 생성
    from fastapi import FastAPI
    from fastapi.responses import PlainTextResponse
    
    app = FastAPI()
    
    error_msg = traceback.format_exc()
    
    @app.get("/{catchall:path}")
    def handle_error(catchall: str):
        return PlainTextResponse(f"Server Init Error:\n\n{error_msg}", status_code=500)
