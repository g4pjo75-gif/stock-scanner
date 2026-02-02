
import sys
import os
import traceback
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

# 현재 파일(api/index.py)의 상위 상위 디렉토리(루트)를 path에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # backend.main에서 app을 가져옵니다.
    from backend.main import app as backend_app
    app = backend_app
except Exception as e:
    # 실패 시 에러 메시지를 보여주는 앱으로 대체
    app = FastAPI()
    error_msg = traceback.format_exc()
    
    @app.get("/{catchall:path}")
    async def handle_error(catchall: str):
        return PlainTextResponse(f"Startup Crash Error:\n\n{error_msg}", status_code=500)
