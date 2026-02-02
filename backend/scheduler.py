"""
스케줄러 모듈 - 매일 22:00 KST 자동 스캔
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, date
import logging

from scanner import AdvancedAnalyzer
from database import save_report, get_scheduler_config, update_last_run

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

analyzer = AdvancedAnalyzer()
scheduler = BackgroundScheduler(timezone="Asia/Seoul")

# 스캔 진행 상태 트래킹용 글로벌 변수
SCAN_PROGRESS = {
    "is_running": False,
    "current_market": None,
    "message": "대기 중",
    "last_update": None
}


def run_daily_scan():
    """일일 스캔 실행 (US & JP)"""
    global SCAN_PROGRESS
    SCAN_PROGRESS["is_running"] = True
    SCAN_PROGRESS["last_update"] = datetime.now().isoformat()
    
    logger.info(f"=== Daily Scan Started at {datetime.now()} ===")
    
    markets = ["US", "JP"]
    for i, market in enumerate(markets):
        try:
            SCAN_PROGRESS["current_market"] = market
            SCAN_PROGRESS["message"] = f"{market} 시장 스캔 중... ({i+1}/{len(markets)})"
            SCAN_PROGRESS["last_update"] = datetime.now().isoformat()
            
            logger.info(f"Scanning {market} market...")
            results = analyzer.scan_market(market=market, top_n=30)
            
            if results:
                save_report(date.today(), market, results)
                logger.info(f"{market} scan completed: {len(results)} items saved")
                SCAN_PROGRESS["message"] = f"{market} 스캔 완료 및 저장됨"
            else:
                logger.warning(f"{market} scan returned no results")
                SCAN_PROGRESS["message"] = f"{market} 결과 없음"
                
        except Exception as e:
            logger.error(f"Error scanning {market}: {e}")
            SCAN_PROGRESS["message"] = f"{market} 스캔 오류: {str(e)}"
    
    SCAN_PROGRESS["is_running"] = False
    SCAN_PROGRESS["current_market"] = None
    SCAN_PROGRESS["message"] = "모든 스캔 완료"
    SCAN_PROGRESS["last_update"] = datetime.now().isoformat()
    update_last_run()
    
    logger.info("=== Daily Scan Completed ===")


def start_scheduler():
    """스케줄러 시작 (DB 설정 로드)"""
    if scheduler.running:
        return

    config = get_scheduler_config()
    if config['enabled']:
        scheduler.add_job(
            run_daily_scan,
            trigger=CronTrigger(hour=config['hour'], minute=config['minute'], timezone="Asia/Seoul"),
            id="daily_scan",
            name="Daily Market Scan",
            replace_existing=True
        )
        scheduler.start()
        logger.info(f"Scheduler started - Daily scan scheduled at {config['hour']:02d}:{config['minute']:02d} KST")
    else:
        scheduler.start() # 시작은 하되 잡은 없음
        logger.info("Scheduler started in disabled state")

def update_schedule(hour: int, minute: int, enabled: bool = True):
    """스케줄 시간 변경 및 즉시 적용"""
    if not scheduler.running:
        scheduler.start()

    if enabled:
        scheduler.add_job(
            run_daily_scan,
            trigger=CronTrigger(hour=hour, minute=minute, timezone="Asia/Seoul"),
            id="daily_scan",
            name="Daily Market Scan",
            replace_existing=True
        )
        logger.info(f"Schedule updated to {hour:02d}:{minute:02d} KST")
    else:
        if scheduler.get_job("daily_scan"):
            scheduler.remove_job("daily_scan")
        logger.info("Schedule disabled")

def get_next_run_time():
    """다음 실행 시간 반환"""
    job = scheduler.get_job("daily_scan")
    if job and job.next_run_time:
        return job.next_run_time.isoformat()
    return None


def stop_scheduler():
    """스케줄러 중지"""
    scheduler.shutdown()
    logger.info("Scheduler stopped")


if __name__ == "__main__":
    # 테스트 실행
    print("Running manual scan...")
    run_daily_scan()
