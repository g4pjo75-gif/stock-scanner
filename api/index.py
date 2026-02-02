
import sys
import os
import traceback
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

# 현재 파일(api/index.py)의 상위 상위 디렉토리(루트)를 path에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 1. 기본 앱 생성 (Vercel 빌드 체크 통과용)
app = FastAPI()

# 2. 실제 백엔드 로드 시도
try:
    from backend.main import app as backend_app
    # 로드 성공 시 앱 교체
    app = backend_app
except Exception as e:
    # 로드 실패 시 에러 내용을 반환하는 핸들러 등록
    error_msg = traceback.format_exc()
    
    @app.get("/{catchall:path}")
    async def handle_startup_error(catchall: str):
        return PlainTextResponse(f"Using Fallback App. Backend Import Error:\n\n{error_msg}", status_code=500)
