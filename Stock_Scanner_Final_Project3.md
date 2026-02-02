3. 백엔드 핵심 로직: 정밀 분석 및 추적 (Python)

import yfinance as yf
from fastapi import FastAPI

app = FastAPI()

class AdvancedAnalyzer:
    def analyze_ticker(self, ticker):
        """특정 종목 실시간/데일리 정밀 분석"""
        df = yf.download(ticker, period="6mo", progress=False)
        if df.empty: return None

        # 1. 지표 계산 (SMA/EMA)
        close = df['Close']
        sma5 = close.rolling(5).mean().iloc[-1]
        sma20 = close.rolling(20).mean().iloc[-1]
        sma40 = close.rolling(40).mean().iloc[-1]
        ema10 = close.ewm(span=10).mean().iloc[-1]

        # 2. 고지로 스테이지 판별
        stage = 6 if sma5 > sma40 > sma20 else (1 if sma5 > sma20 > sma40 else 0)

        # 3. 쿨라메기 VCP 및 필터
        avg_vol = df['Volume'].rolling(20).mean().iloc[-2]
        vol_surge = df['Volume'].iloc[-1] >= (avg_vol * 2.0)
        adr = ((df['High'] - df['Low']) / df['Low']).rolling(20).mean().iloc[-1]
        dist_ok = (close.iloc[-1] - ema10) / ema10 <= adr

        # 4. 종합 어드바이스 생성
        advice = "관망"
        if stage == 6 and vol_surge: advice = "🚀 [매수급소] 강력 매수"
        elif stage == 1 and dist_ok: advice = "📈 [안정상승] 보유 및 눌림목 매수"
        elif close.iloc[-1] < sma20: advice = "🚨 [매도경고] 추세 이탈 위험"

        return {
            "ticker": ticker, "price": round(close.iloc[-1], 2),
            "stage": stage, "vol_surge": vol_surge, "dist_ok": dist_ok,
            "advice": advice, "stop_loss": round(sma20, 2)
        }

# API: 특정 티커 검색 분석
@app.get("/api/analyze/{ticker}")
async def get_analysis(ticker: str):
    analyzer = AdvancedAnalyzer()
    return analyzer.analyze_ticker(ticker)

# API: 내 포트폴리오 실시간 상태 업데이트
@app.get("/api/portfolio/status")
async def get_portfolio_status():
    # DB에서 active한 종목 리스트를 가져와 analyze_ticker 실행 후 반환
    pass