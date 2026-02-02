
import sys
import os

# 현재 파일(api/index.py)의 상위 상위 디렉토리(루트)를 path에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app

# Vercel은 'app'이라는 변수를 찾아서 실행함
