"""
데이터베이스 모듈 - SQLite/Turso(LibSQL) 지원
"""
import os
import sys
from datetime import datetime, date
from typing import List, Dict, Optional
import json

# Turso 환경변수 확인
TURSO_DATABASE_URL = os.environ.get("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.environ.get("TURSO_AUTH_TOKEN")

# Turso 사용 여부 결정
USE_TURSO = bool(TURSO_DATABASE_URL and TURSO_AUTH_TOKEN)

if USE_TURSO:
    # Turso/LibSQL 사용
    import libsql_experimental as libsql
else:
    # 로컬 SQLite 사용
    import sqlite3

# 로컬 SQLite 데이터베이스 경로 설정 (Turso 미사용 시)
if getattr(sys, 'frozen', False):
    # PyInstaller EXE 실행 환경
    base_dir = os.path.dirname(sys.executable)
    DB_PATH = os.path.join(base_dir, "data", "scanner.db")
elif os.environ.get("VERCEL") and not USE_TURSO:
    # Vercel Serverless 환경 (Turso 없으면 /tmp 사용)
    DB_PATH = "/tmp/scanner.db"
else:
    # 일반 Python 실행 환경
    base_dir = os.path.dirname(os.path.dirname(__file__))
    DB_PATH = os.path.join(base_dir, "data", "scanner.db")


def get_connection():
    """데이터베이스 연결 생성"""
    if USE_TURSO:
        # Turso 원격 데이터베이스 연결
        conn = libsql.connect(
            database=TURSO_DATABASE_URL,
            auth_token=TURSO_AUTH_TOKEN
        )
        return conn
    else:
        # 로컬 SQLite 연결
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn


def check_and_init_db():
    """DB 초기화 (Turso 또는 로컬)"""
    if USE_TURSO:
        # Turso는 항상 초기화 시도 (테이블 없으면 생성)
        init_database()
    elif not os.path.exists(DB_PATH):
        init_database()


def init_database():
    """데이터베이스 테이블 초기화"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. 날짜별 스캔 리포트 (날짜+시장 조합이 고유)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_reports (
            report_id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_date DATE NOT NULL,
            market VARCHAR(5) NOT NULL,
            total_count INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(report_date, market)
        )
    """)
    
    # 2. 리포트에 포함된 종목 상세 정보
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS report_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_date DATE NOT NULL,
            market VARCHAR(5) NOT NULL,
            ticker VARCHAR(20) NOT NULL,
            name VARCHAR(100),
            price REAL,
            change_pct REAL,
            stage INTEGER,
            score INTEGER,
            vcp_ratio REAL,
            vol_surge INTEGER,
            advice TEXT,
            stop_loss REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 3. 내 포트폴리오
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_portfolio (
            portfolio_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker VARCHAR(20) NOT NULL,
            name VARCHAR(100),
            market VARCHAR(5),
            entry_date DATE,
            entry_price REAL,
            entry_stage INTEGER,
            entry_score INTEGER DEFAULT 0,
            current_status VARCHAR(20) DEFAULT 'HOLDING',
            stop_loss REAL,
            target_price REAL,
            quantity INTEGER,
            memo TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 4. 스케줄러 설정
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scheduler_config (
            id INTEGER PRIMARY KEY,
            enabled INTEGER DEFAULT 1,
            hour INTEGER DEFAULT 22,
            minute INTEGER DEFAULT 0,
            last_run TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 스케줄러 기본 설정 삽입 (없으면)
    cursor.execute("SELECT COUNT(*) FROM scheduler_config")
    count_result = cursor.fetchone()
    count = count_result[0] if count_result else 0
    if count == 0:
        cursor.execute("INSERT INTO scheduler_config (id, enabled, hour, minute) VALUES (1, 1, 22, 0)")
    
    conn.commit()
    conn.close()


def _row_to_dict(row, cursor_description=None):
    """행 데이터를 딕셔너리로 변환 (SQLite Row 또는 Turso tuple 대응)"""
    if row is None:
        return None
    if hasattr(row, 'keys'):
        # sqlite3.Row 객체
        return dict(row)
    elif cursor_description:
        # Turso tuple + cursor.description
        columns = [col[0] for col in cursor_description]
        return dict(zip(columns, row))
    else:
        return row


# === Daily Reports ===
def save_report(report_date: date, market: str, items: List[Dict]):
    """일일 리포트 저장"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 기존 리포트 삭제
    cursor.execute("DELETE FROM report_items WHERE report_date = ? AND market = ?", 
                   (report_date.isoformat(), market))
    cursor.execute("DELETE FROM daily_reports WHERE report_date = ? AND market = ?", 
                   (report_date.isoformat(), market))
    
    # 리포트 헤더 저장
    cursor.execute("""
        INSERT INTO daily_reports (report_date, market, total_count)
        VALUES (?, ?, ?)
    """, (report_date.isoformat(), market, len(items)))
    
    # 리포트 아이템 저장
    for item in items:
        cursor.execute("""
            INSERT INTO report_items 
            (report_date, market, ticker, name, price, change_pct, stage, score, 
             vcp_ratio, vol_surge, advice, stop_loss)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report_date.isoformat(), market, item['ticker'], item.get('name', ''),
            item.get('price', 0), item.get('change_pct', 0), item.get('stage', 0),
            item.get('score', 0), item.get('vcp_ratio', 0), item.get('vol_surge', 0),
            item.get('advice', ''), item.get('stop_loss', 0)
        ))
    
    conn.commit()
    conn.close()


def get_report(report_date: date, market: str) -> List[Dict]:
    """특정 날짜 리포트 조회"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM report_items 
        WHERE report_date = ? AND market = ?
        ORDER BY score DESC
    """, (report_date.isoformat(), market))
    
    rows = cursor.fetchall()
    description = cursor.description
    conn.close()
    
    return [_row_to_dict(row, description) for row in rows]


def get_report_dates(market: str, limit: int = 30) -> List[str]:
    """리포트가 있는 날짜 목록 조회"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT DISTINCT report_date FROM daily_reports 
        WHERE market = ?
        ORDER BY report_date DESC
        LIMIT ?
    """, (market, limit))
    
    rows = cursor.fetchall()
    description = cursor.description
    conn.close()
    
    return [_row_to_dict(row, description)['report_date'] for row in rows]


# === Portfolio ===
def add_to_portfolio(data: Dict) -> int:
    """포트폴리오에 종목 추가"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO user_portfolio 
        (ticker, name, market, entry_date, entry_price, entry_stage, entry_score, stop_loss, target_price, quantity, memo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data['ticker'], data.get('name', ''), data.get('market', 'US'),
        data.get('entry_date', date.today().isoformat()),
        data.get('entry_price', 0), data.get('entry_stage', 0), data.get('entry_score', 0),
        data.get('stop_loss', 0), data.get('target_price', 0),
        data.get('quantity', 0), data.get('memo', '')
    ))
    
    portfolio_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return portfolio_id


def get_portfolio(status: str = None) -> List[Dict]:
    """포트폴리오 조회"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if status:
        cursor.execute("""
            SELECT * FROM user_portfolio WHERE current_status = ?
            ORDER BY entry_date DESC
        """, (status,))
    else:
        cursor.execute("SELECT * FROM user_portfolio ORDER BY entry_date DESC")
    
    rows = cursor.fetchall()
    description = cursor.description
    conn.close()
    
    return [_row_to_dict(row, description) for row in rows]


def update_portfolio(portfolio_id: int, data: Dict):
    """포트폴리오 업데이트"""
    conn = get_connection()
    cursor = conn.cursor()
    
    updates = []
    values = []
    for key, value in data.items():
        if key != 'portfolio_id':
            updates.append(f"{key} = ?")
            values.append(value)
    
    values.append(datetime.now().isoformat())
    values.append(portfolio_id)
    
    cursor.execute(f"""
        UPDATE user_portfolio 
        SET {', '.join(updates)}, updated_at = ?
        WHERE portfolio_id = ?
    """, values)
    
    conn.commit()
    conn.close()


def delete_from_portfolio(portfolio_id: int):
    """포트폴리오에서 삭제"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_portfolio WHERE portfolio_id = ?", (portfolio_id,))
    conn.commit()
    conn.close()


# === Scheduler Config ===
def get_scheduler_config() -> Dict:
    """스케줄러 설정 조회"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM scheduler_config WHERE id = 1")
    row = cursor.fetchone()
    description = cursor.description
    conn.close()
    result = _row_to_dict(row, description)
    return result if result else {"enabled": 1, "hour": 22, "minute": 0}


def update_scheduler_config(enabled: int, hour: int, minute: int):
    """스케줄러 설정 업데이트"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE scheduler_config 
        SET enabled = ?, hour = ?, minute = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = 1
    """, (enabled, hour, minute))
    conn.commit()
    conn.close()


def update_last_run():
    """마지막 실행 시간 업데이트"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE scheduler_config 
        SET last_run = CURRENT_TIMESTAMP 
        WHERE id = 1
    """)
    conn.commit()
    conn.close()


# 초기화 실행
init_database()
