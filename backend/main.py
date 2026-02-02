"""
FastAPI 메인 서버
"""
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
import os
import sys
import logging

from scanner import AdvancedAnalyzer, calculate_position_size, US_TICKERS, JP_TICKERS
from database import (
    save_report, get_report, get_report_dates,
    add_to_portfolio, get_portfolio, update_portfolio, delete_from_portfolio,
    get_scheduler_config, update_scheduler_config
)
from scheduler import (
    start_scheduler, update_schedule, get_next_run_time, run_daily_scan,
    SCAN_PROGRESS
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="글로벌 이평선 대순환 & 모멘텀 스캐너",
    description="JP/US 시장 주식 스캐너 API",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 서빙
if getattr(sys, 'frozen', False):
    # PyInstaller EXE 실행 환경
    base_path = sys._MEIPASS
else:
    # 일반 Python 실행 환경
    base_path = os.path.dirname(os.path.dirname(__file__))

frontend_path = os.path.join(base_path, "frontend")

if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

# 캐시 비활성화 미들웨어 (JS/CSS 파일)
from starlette.middleware.base import BaseHTTPMiddleware

class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/static/js/") or request.url.path.startswith("/static/css/"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

app.add_middleware(NoCacheMiddleware)

# 분석기 인스턴스
analyzer = AdvancedAnalyzer()


# === Pydantic Models ===
class PortfolioCreate(BaseModel):
    ticker: str
    name: Optional[str] = ""
    market: Optional[str] = "US"
    entry_date: Optional[str] = None
    entry_price: Optional[float] = 0
    entry_stage: Optional[int] = 0
    entry_score: Optional[int] = 0
    stop_loss: Optional[float] = 0
    target_price: Optional[float] = 0
    quantity: Optional[int] = 0
    memo: Optional[str] = ""

class PortfolioUpdate(BaseModel):
    current_status: Optional[str] = None
    stop_loss: Optional[float] = None
    target_price: Optional[float] = None
    memo: Optional[str] = None

class PositionCalcRequest(BaseModel):
    total_capital: float
    current_price: float
    stop_loss_price: float
    risk_pct: Optional[float] = 1.0

class SchedulerUpdate(BaseModel):
    hour: int
    minute: int

class SchedulerToggle(BaseModel):
    enabled: bool


# === 메인 페이지 ===
@app.get("/")
async def root():
    """메인 대시보드 페이지"""
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "글로벌 이평선 대순환 & 모멘텀 스캐너 API"}


# === 스캔 API ===
@app.get("/api/scan")
async def scan_market(
    market: str = Query("US", description="시장 선택 (US/JP)"),
    top_n: int = Query(20, description="상위 N개 종목")
):
    """시장 전체 스캔"""
    try:
        results = analyzer.scan_market(market=market.upper(), top_n=top_n)
        
        # 결과를 DB에 저장
        if results:
            save_report(date.today(), market.upper(), results)
        
        return {
            "market": market.upper(),
            "date": date.today().isoformat(),
            "count": len(results),
            "items": results
        }
    except Exception as e:
        logger.error(f"Scan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chart/{ticker}")
async def get_chart_data(
    ticker: str,
    period: str = Query("6mo", description="기간 (1mo, 3mo, 6mo, 1y, 2y)")
):
    """차트용 OHLCV 데이터 + 이동평균선"""
    try:
        import yfinance as yf
        import pandas as pd
        import numpy as np
        
        df = yf.download(ticker.upper(), period=period, progress=False)
        if df.empty:
            raise HTTPException(status_code=404, detail="데이터를 찾을 수 없습니다")
        
        # MultiIndex 컬럼 처리 (yfinance 최신 버전 대응)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # 이동평균선 계산
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA40'] = df['Close'].rolling(window=40).mean()
        
        # Lightweight Charts 형식으로 변환
        candles = []
        volumes = []
        ma5_data = []
        ma20_data = []
        ma40_data = []
        
        for idx, row in df.iterrows():
            time_str = idx.strftime('%Y-%m-%d')
            
            # 값 추출 헬퍼 함수
            def get_scalar(val):
                if isinstance(val, (pd.Series, np.ndarray)):
                    return float(val.iloc[0]) if hasattr(val, 'iloc') else float(val[0])
                return float(val)
            
            # 캔들 데이터
            candles.append({
                "time": time_str,
                "open": round(get_scalar(row['Open']), 2),
                "high": round(get_scalar(row['High']), 2),
                "low": round(get_scalar(row['Low']), 2),
                "close": round(get_scalar(row['Close']), 2)
            })
            
            # 거래량 데이터 (상승/하락 색상 구분)
            close_val = get_scalar(row['Close'])
            open_val = get_scalar(row['Open'])
            is_up = close_val >= open_val
            volumes.append({
                "time": time_str,
                "value": int(get_scalar(row['Volume'])),
                "color": "rgba(38, 166, 154, 0.5)" if is_up else "rgba(239, 83, 80, 0.5)"
            })
            
            # 이동평균선 데이터
            def is_valid(val):
                try:
                    notna_result = pd.notna(val)
                    if hasattr(notna_result, 'all'):
                        return notna_result.all()
                    return bool(notna_result)
                except:
                    return False
            
            ma5_val = row['MA5']
            ma20_val = row['MA20']
            ma40_val = row['MA40']
            
            if is_valid(ma5_val):
                ma5_data.append({"time": time_str, "value": round(get_scalar(ma5_val), 2)})
            if is_valid(ma20_val):
                ma20_data.append({"time": time_str, "value": round(get_scalar(ma20_val), 2)})
            if is_valid(ma40_val):
                ma40_data.append({"time": time_str, "value": round(get_scalar(ma40_val), 2)})
        
        return {
            "ticker": ticker.upper(),
            "candles": candles,
            "volumes": volumes,
            "ma5": ma5_data,
            "ma20": ma20_data,
            "ma40": ma40_data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chart data error for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analyze/{ticker}")
async def analyze_ticker(ticker: str):
    """개별 종목 분석"""
    try:
        result = analyzer.analyze_ticker(ticker.upper())
        if result is None:
            raise HTTPException(status_code=404, detail="종목을 찾을 수 없습니다")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analyze error for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tickers")
async def get_tickers(market: str = Query("US", description="시장 선택")):
    """시장별 종목 리스트"""
    tickers = US_TICKERS if market.upper() == "US" else JP_TICKERS
    return {"market": market.upper(), "tickers": tickers}


# === 리포트 API ===
@app.get("/api/reports")
async def get_reports(
    market: str = Query("US", description="시장 선택"),
    report_date: Optional[str] = Query(None, description="날짜 (YYYY-MM-DD)")
):
    """저장된 리포트 조회"""
    try:
        if report_date:
            target_date = datetime.strptime(report_date, "%Y-%m-%d").date()
        else:
            target_date = date.today()
        
        items = get_report(target_date, market.upper())
        return {
            "market": market.upper(),
            "date": target_date.isoformat(),
            "count": len(items),
            "items": items
        }
    except Exception as e:
        logger.error(f"Report error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reports/dates")
async def get_available_dates(market: str = Query("US")):
    """리포트가 있는 날짜 목록"""
    dates = get_report_dates(market.upper())
    return {"market": market.upper(), "dates": dates}


# === 포트폴리오 API ===
@app.get("/api/portfolio")
async def list_portfolio(status: Optional[str] = Query(None)):
    """포트폴리오 조회"""
    items = get_portfolio(status)
    
    # 현재 상태 업데이트
    for item in items:
        if item.get("current_status") == "HOLDING":
            ticker = item.get("ticker")
            analysis = analyzer.analyze_ticker(ticker)
            if analysis:
                item["current_price"] = analysis.get("price", 0)
                item["current_stage"] = analysis.get("stage", 0)
                item["current_advice"] = analysis.get("advice", "")
                
                entry_price = item.get("entry_price", 0)
                if entry_price > 0:
                    item["profit_pct"] = round(
                        ((analysis.get("price", 0) - entry_price) / entry_price) * 100, 2
                    )
    
    return {"count": len(items), "items": items}


@app.post("/api/portfolio")
async def create_portfolio(data: PortfolioCreate):
    """포트폴리오에 종목 추가"""
    try:
        portfolio_id = add_to_portfolio(data.dict())
        return {"success": True, "portfolio_id": portfolio_id}
    except Exception as e:
        logger.error(f"Portfolio create error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/portfolio/{portfolio_id}")
async def modify_portfolio(portfolio_id: int, data: PortfolioUpdate):
    """포트폴리오 수정"""
    try:
        update_data = {k: v for k, v in data.dict().items() if v is not None}
        update_portfolio(portfolio_id, update_data)
        return {"success": True}
    except Exception as e:
        logger.error(f"Portfolio update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/portfolio/{portfolio_id}")
async def remove_portfolio(portfolio_id: int):
    """포트폴리오에서 삭제"""
    try:
        delete_from_portfolio(portfolio_id)
        return {"success": True}
    except Exception as e:
        logger.error(f"Portfolio delete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# === 스케줄러 API ===
@app.get("/api/scheduler/status")
async def get_scheduler_status():
    """스케줄러 상태 조회"""
    config = get_scheduler_config()
    next_run = get_next_run_time()
    return {
        "enabled": bool(config['enabled']),
        "hour": config['hour'],
        "minute": config['minute'],
        "next_run": next_run,
        "last_run": config.get('last_run')
    }

@app.post("/api/scheduler/update")
async def update_scheduler_api(data: SchedulerUpdate):
    """스케줄 시간 변경"""
    try:
        config = get_scheduler_config()
        update_scheduler_config(int(config['enabled']), data.hour, data.minute)
        update_schedule(data.hour, data.minute, bool(config['enabled']))
        return {"success": True}
    except Exception as e:
        logger.error(f"Scheduler update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/scheduler/toggle")
async def toggle_scheduler_api(data: SchedulerToggle):
    """스케줄러 ON/OFF"""
    try:
        config = get_scheduler_config()
        update_scheduler_config(1 if data.enabled else 0, config['hour'], config['minute'])
        update_schedule(config['hour'], config['minute'], data.enabled)
        return {"success": True}
    except Exception as e:
        logger.error(f"Scheduler toggle error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/scheduler/run")
async def run_manual_scan_api(background_tasks: BackgroundTasks):
    """수동 스캔 즉시 실행 (백그라운드)"""
    try:
        if SCAN_PROGRESS["is_running"]:
            return {"success": False, "message": "이미 스캔이 진행 중입니다."}
            
        background_tasks.add_task(run_daily_scan)
        return {"success": True, "message": "스캔이 시작되었습니다."}
    except Exception as e:
        logger.error(f"Manual scan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/scheduler/progress")
async def get_scheduler_progress():
    """스케줄러 진행 상태 조회"""
    return SCAN_PROGRESS

@app.get("/api/scheduler/reports")
async def get_scheduler_dates():
    """스케줄로 생성된 리포트 날짜 목록 (일반 리포트와 동일하게 사용 가능)"""
    # 기존 get_report_dates와 동일하거나 구분 필요시 사용
    dates = get_report_dates("US") # 기본 US
    return {"dates": dates}


# === 포지션 계산기 ===
@app.post("/api/calculate-position")
async def calc_position(data: PositionCalcRequest):
    """포지션 사이즈 계산 (1% 리스크 관리)"""
    result = calculate_position_size(
        data.total_capital,
        data.current_price,
        data.stop_loss_price,
        data.risk_pct
    )
    return result


# === 서버 상태 ===
@app.get("/api/health")
async def health_check():
    """서버 상태 확인"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

# 루트 경로 핸들러 (Vercel 배포 시 필요)
from fastapi.responses import FileResponse
@app.get("/")
async def read_root():
    return FileResponse(os.path.join(frontend_path, "index.html"))


@app.on_event("startup")
async def startup_event():
    """서버 시작 시 스케줄러 자동 실행"""
    # Vercel 환경에서는 스케줄러 실행하지 않음 (Serverless Function은 지속 실행되지 않음)
    if not os.environ.get("VERCEL"):
        start_scheduler()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
