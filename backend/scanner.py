"""
주식 스캐너 모듈 - 고지로 스테이지 & 쿨라메기 모멘텀 분석
"""
import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 시장별 종목 리스트
US_TICKERS = [
    # S&P 500 주요 종목 (시가총액 상위)
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "UNH", "JNJ",
    "XOM", "JPM", "V", "PG", "MA", "HD", "CVX", "MRK", "ABBV", "LLY",
    "PEP", "KO", "COST", "AVGO", "TMO", "MCD", "WMT", "CSCO", "ACN", "DHR",
    "ABT", "CRM", "ADBE", "NKE", "TXN", "NEE", "PM", "UNP", "RTX", "ORCL",
    "AMD", "INTC", "QCOM", "IBM", "NOW", "INTU", "AMAT", "ISRG", "CAT", "GE",
    "BA", "HON", "AMGN", "LOW", "SBUX", "GS", "BLK", "AXP", "BKNG", "MDLZ",
    "GILD", "ADI", "REGN", "VRTX", "CME", "SYK", "ZTS", "LRCX", "MMC", "CB",
    "PLD", "EOG", "MO", "DUK", "SO", "CI", "CL", "USB", "BDX", "PSA",
    "PYPL", "SQ", "SHOP", "SNOW", "PLTR", "CRWD", "NET", "DDOG", "ZS", "PANW"
]

JP_TICKERS = [
    # Nikkei 225 주요 종목
    "7203.T", "6758.T", "9984.T", "6861.T", "8306.T", "9432.T", "6501.T", "7267.T", "4502.T", "4503.T",
    "6902.T", "7751.T", "8035.T", "6367.T", "7974.T", "4063.T", "8411.T", "6098.T", "6273.T", "8766.T",
    "6954.T", "9433.T", "4519.T", "6857.T", "8031.T", "7741.T", "4661.T", "6762.T", "3382.T", "6752.T",
    "8058.T", "2914.T", "6971.T", "4543.T", "6594.T", "7269.T", "8316.T", "4568.T", "7201.T", "9983.T"
]


class AdvancedAnalyzer:
    """고급 주식 분석기"""
    
    def __init__(self):
        self.cache = {}
    
    def get_stock_data(self, ticker: str, period: str = "6mo") -> Optional[pd.DataFrame]:
        """주식 데이터 가져오기"""
        try:
            df = yf.download(ticker, period=period, progress=False)
            if df.empty:
                return None
            return df
        except Exception as e:
            logger.error(f"Error fetching {ticker}: {e}")
            return None
    
    def check_gojiro_stage(self, df: pd.DataFrame) -> int:
        """
        고지로 스테이지 판별 (1~6)
        - Stage 1: 5 > 20 > 40 (정배열 상승)
        - Stage 2: 20 > 5 > 40 (단기 조정)
        - Stage 3: 20 > 40 > 5 (하락 전환)
        - Stage 4: 40 > 20 > 5 (역배열 하락)
        - Stage 5: 40 > 5 > 20 (바닥 다지기)
        - Stage 6: 5 > 40 > 20 (상승 반전 - 매수 급소!)
        """
        if df is None or len(df) < 40:
            return 0
        
        close = df['Close']
        sma5 = close.rolling(5).mean().iloc[-1]
        sma20 = close.rolling(20).mean().iloc[-1]
        sma40 = close.rolling(40).mean().iloc[-1]
        
        # 스칼라 값으로 변환
        if hasattr(sma5, 'item'):
            sma5 = sma5.item()
        if hasattr(sma20, 'item'):
            sma20 = sma20.item()
        if hasattr(sma40, 'item'):
            sma40 = sma40.item()
        
        if sma5 > sma20 > sma40:
            return 1  # 정배열 상승
        elif sma20 > sma5 > sma40:
            return 2  # 단기 조정
        elif sma20 > sma40 > sma5:
            return 3  # 하락 전환
        elif sma40 > sma20 > sma5:
            return 4  # 역배열 하락
        elif sma40 > sma5 > sma20:
            return 5  # 바닥 다지기
        elif sma5 > sma40 > sma20:
            return 6  # 상승 반전! 🚀
        
        return 0
    
    def check_kullamagi_setup(self, df: pd.DataFrame) -> Dict:
        """
        쿨라메기 모멘텀 & VCP 분석
        - 3개월 내 30%+ 상승 여부
        - 최근 변동성 수축 (VCP) 여부
        """
        if df is None or len(df) < 60:
            return {"momentum": False, "vcp": False, "vcp_ratio": 0}
        
        close = df['Close']
        
        # 3개월 모멘텀 (30%+ 상승)
        price_3m_ago = close.iloc[-60] if len(close) >= 60 else close.iloc[0]
        current_price = close.iloc[-1]
        
        if hasattr(price_3m_ago, 'item'):
            price_3m_ago = price_3m_ago.item()
        if hasattr(current_price, 'item'):
            current_price = current_price.item()
            
        momentum_pct = ((current_price - price_3m_ago) / price_3m_ago) * 100
        has_momentum = momentum_pct >= 30
        
        # VCP (Volatility Contraction Pattern)
        recent_volatility = close.iloc[-5:].std()
        past_volatility = close.iloc[-20:-5].std()
        
        if hasattr(recent_volatility, 'item'):
            recent_volatility = recent_volatility.item()
        if hasattr(past_volatility, 'item'):
            past_volatility = past_volatility.item()
        
        vcp_ratio = recent_volatility / past_volatility if past_volatility > 0 else 1
        has_vcp = vcp_ratio < 0.8  # 변동성 20% 이상 수축
        
        return {
            "momentum": has_momentum,
            "momentum_pct": round(momentum_pct, 2),
            "vcp": has_vcp,
            "vcp_ratio": round(vcp_ratio, 2)
        }
    
    def check_volume_surge(self, df: pd.DataFrame) -> Dict:
        """거래량 폭증 분석"""
        if df is None or len(df) < 20:
            return {"surge": False, "ratio": 0}
        
        volume = df['Volume']
        avg_vol_20 = volume.iloc[-21:-1].mean()
        current_vol = volume.iloc[-1]
        
        if hasattr(avg_vol_20, 'item'):
            avg_vol_20 = avg_vol_20.item()
        if hasattr(current_vol, 'item'):
            current_vol = current_vol.item()
        
        vol_ratio = current_vol / avg_vol_20 if avg_vol_20 > 0 else 0
        
        return {
            "surge": vol_ratio >= 2.0,  # 200% 이상
            "ratio": round(vol_ratio, 2)
        }
    
    def check_distance_filter(self, df: pd.DataFrame) -> Dict:
        """이격도 필터 (ADR 기준)"""
        if df is None or len(df) < 20:
            return {"ok": False, "distance_pct": 0}
        
        close = df['Close']
        high = df['High']
        low = df['Low']
        
        # EMA 10
        ema10 = close.ewm(span=10).mean().iloc[-1]
        current_price = close.iloc[-1]
        
        # ADR (Average Daily Range)
        daily_range = (high - low) / low
        adr = daily_range.rolling(20).mean().iloc[-1]
        
        if hasattr(ema10, 'item'):
            ema10 = ema10.item()
        if hasattr(current_price, 'item'):
            current_price = current_price.item()
        if hasattr(adr, 'item'):
            adr = adr.item()
        
        distance_pct = abs((current_price - ema10) / ema10)
        
        return {
            "ok": distance_pct <= adr,  # ADR 이내면 OK
            "distance_pct": round(distance_pct * 100, 2),
            "adr_pct": round(adr * 100, 2)
        }
    
    def calculate_score(self, stage: int, kullamagi: Dict, volume: Dict, distance: Dict) -> int:
        """종합 점수 계산 (0~100)"""
        score = 0
        
        # 스테이지 점수 (최대 40점)
        stage_scores = {1: 35, 6: 40, 2: 20, 5: 25, 3: 10, 4: 5, 0: 0}
        score += stage_scores.get(stage, 0)
        
        # 모멘텀 점수 (최대 20점)
        if kullamagi.get("momentum"):
            score += 15
        if kullamagi.get("vcp"):
            score += 5
        
        # 거래량 점수 (최대 20점)
        if volume.get("surge"):
            score += 20
        elif volume.get("ratio", 0) >= 1.5:
            score += 10
        
        # 이격도 점수 (최대 20점)
        if distance.get("ok"):
            score += 20
        elif distance.get("distance_pct", 100) < 5:
            score += 10
        
        return min(score, 100)
    
    def generate_advice(self, stage: int, score: int, volume: Dict, distance: Dict) -> str:
        """어드바이스 생성"""
        if stage == 6 and volume.get("surge") and distance.get("ok"):
            return "🚀 [매수급소] 강력 매수 - 스테이지 6 + 거래량 폭증"
        elif stage == 6 and distance.get("ok"):
            return "🚀 [매수급소] 상승 반전 포착 - 스테이지 6 진입"
        elif stage == 1 and distance.get("ok"):
            return "📈 [안정상승] 정배열 유지 - 홀딩 또는 눌림목 매수"
        elif stage == 1 and not distance.get("ok"):
            return "⚠️ [주의] 정배열이나 과열 - 추격 매수 금지"
        elif stage == 5:
            return "👀 [관심] 바닥 다지기 - 스테이지 6 전환 대기"
        elif stage in [3, 4]:
            return "🚨 [매도경고] 추세 하락 - 손절가 점검"
        elif stage == 2:
            return "📊 [조정] 단기 조정 구간 - 지지선 확인"
        else:
            return "📋 [관망] 추가 분석 필요"
    
    def analyze_ticker(self, ticker: str) -> Optional[Dict]:
        """종목 종합 분석"""
        df = self.get_stock_data(ticker)
        if df is None or len(df) < 40:
            return None
        
        try:
            # 기본 정보
            stock = yf.Ticker(ticker)
            info = stock.info
            name = info.get('shortName', info.get('longName', ticker))
            
            # 현재가 및 등락률
            current_price = df['Close'].iloc[-1]
            prev_price = df['Close'].iloc[-2] if len(df) > 1 else current_price
            
            if hasattr(current_price, 'item'):
                current_price = current_price.item()
            if hasattr(prev_price, 'item'):
                prev_price = prev_price.item()
                
            change_pct = ((current_price - prev_price) / prev_price) * 100
            
            # 분석 실행
            stage = self.check_gojiro_stage(df)
            kullamagi = self.check_kullamagi_setup(df)
            volume = self.check_volume_surge(df)
            distance = self.check_distance_filter(df)
            
            # 점수 및 어드바이스
            score = self.calculate_score(stage, kullamagi, volume, distance)
            advice = self.generate_advice(stage, score, volume, distance)
            
            # 손절가 (20일선)
            sma20 = df['Close'].rolling(20).mean().iloc[-1]
            if hasattr(sma20, 'item'):
                sma20 = sma20.item()
            
            return {
                "ticker": ticker,
                "name": name,
                "price": round(current_price, 2),
                "change_pct": round(change_pct, 2),
                "stage": stage,
                "score": score,
                "momentum_pct": kullamagi.get("momentum_pct", 0),
                "vcp_ratio": kullamagi.get("vcp_ratio", 1),
                "vol_surge": 1 if volume.get("surge") else 0,
                "vol_ratio": volume.get("ratio", 0),
                "distance_ok": distance.get("ok", False),
                "distance_pct": distance.get("distance_pct", 0),
                "advice": advice,
                "stop_loss": round(sma20, 2)
            }
        except Exception as e:
            logger.error(f"Error analyzing {ticker}: {e}")
            return None
    
    def scan_market(self, market: str = "US", top_n: int = 20) -> List[Dict]:
        """시장 전체 스캔"""
        tickers = US_TICKERS if market == "US" else JP_TICKERS
        results = []
        
        logger.info(f"Scanning {market} market ({len(tickers)} tickers)...")
        
        for ticker in tickers:
            result = self.analyze_ticker(ticker)
            if result and result.get("stage") in [1, 5, 6]:  # 관심 스테이지만
                results.append(result)
        
        # 점수순 정렬
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        return results[:top_n]
    
    def get_stage_description(self, stage: int) -> str:
        """스테이지 설명"""
        descriptions = {
            1: "정배열 상승 (5>20>40)",
            2: "단기 조정 (20>5>40)",
            3: "하락 전환 (20>40>5)",
            4: "역배열 하락 (40>20>5)",
            5: "바닥 다지기 (40>5>20)",
            6: "상승 반전 🚀 (5>40>20)"
        }
        return descriptions.get(stage, "분석 불가")


def calculate_position_size(total_capital: float, current_price: float, stop_loss_price: float, risk_pct: float = 1.0) -> Dict:
    """
    포지션 사이즈 계산 (1% 리스크 관리)
    - total_capital: 총 투자금
    - current_price: 현재가
    - stop_loss_price: 손절가
    - risk_pct: 리스크 비율 (기본 1%)
    """
    risk_amount = total_capital * (risk_pct / 100)  # 1%면 총자본의 1%
    loss_per_share = current_price - stop_loss_price
    
    if loss_per_share <= 0:
        return {"error": "손절가가 현재가보다 높습니다"}
    
    shares = int(risk_amount / loss_per_share)
    position_value = shares * current_price
    
    return {
        "shares": shares,
        "position_value": round(position_value, 2),
        "risk_amount": round(risk_amount, 2),
        "loss_per_share": round(loss_per_share, 2),
        "position_pct": round((position_value / total_capital) * 100, 2)
    }
