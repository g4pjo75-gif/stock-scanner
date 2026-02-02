2. 데이터베이스 설계 (MariaDB)
PC 환경에 최적화된 가벼운 MariaDB 테이블 구조입니다.

-- 1. 날짜별 스캔 리포트 저장 (저녁 10시 자동 생성)
CREATE TABLE daily_reports (
    report_id INT AUTO_INCREMENT PRIMARY KEY,
    report_date DATE UNIQUE NOT NULL,
    total_count INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 리포트에 포함된 종목 상세 정보
CREATE TABLE report_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    report_date DATE,
    ticker VARCHAR(20) NOT NULL,
    market VARCHAR(5), -- 'JP', 'US'
    price DECIMAL(12, 2),
    stage INT,         -- 1~6
    score INT,         -- 정밀도 점수 (0~100)
    vcp_ratio DECIMAL(5, 2),
    advice TEXT,       -- 매수/매도 어드바이스
    stop_loss DECIMAL(12, 2),
    FOREIGN KEY (report_date) REFERENCES daily_reports(report_date)
);

-- 3. 내 포트폴리오 (내가 실제로 매수한 종목 추적)
CREATE TABLE user_portfolio (
    portfolio_id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    market VARCHAR(5),
    entry_date DATE,
    entry_price DECIMAL(12, 2),
    entry_stage INT,
    current_status VARCHAR(20) DEFAULT 'HOLDING', -- 'HOLDING', 'SOLD'
    stop_loss DECIMAL(12, 2),
    memo TEXT
);