"""
Планировщик задач для расчета долгов - только 15 числа
"""
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .debt_calculator import update_all_debts

logger = logging.getLogger(__name__)


def calculate_debts_job():
    """Задача: расчет долгов 15 числа каждого месяца в 00:00"""
    print(f"[{datetime.now()}] Running monthly debt calculation job...")
    try:
        result = update_all_debts()
        print(f"[{datetime.now()}] Debt calculation completed: {result}")
    except Exception as e:
        print(f"[{datetime.now()}] Error in debt calculation: {e}")


def start_scheduler():
    """Запуск планировщика задач"""
    try:
        scheduler = BackgroundScheduler(timezone='Europe/Moscow')
        
        # Только одна задача: расчет долгов 15 числа каждого месяца в 00:00
        scheduler.add_job(
            calculate_debts_job,
            trigger=CronTrigger(day=15, hour=0, minute=0),
            id="calculate_debts_monthly",
            name="Расчет долгов 15 числа",
            replace_existing=True,
        )
        
        scheduler.start()
        print("=" * 60)
        print("SCHEDULER STARTED SUCCESSFULLY")
        print("=" * 60)
        print("Jobs scheduled:")
        print("  - Monthly debt calculation: 15th day of each month at 00:00")
        print("=" * 60)
        print(f"Current time: {datetime.now()}")
        print(f"Next run: {scheduler.get_job('calculate_debts_monthly').next_run_time}")
        print("=" * 60)
        return scheduler
    except Exception as e:
        print(f"Error starting scheduler: {e}")
        return None


def stop_scheduler():
    """Остановка планировщика"""
    global scheduler
    if scheduler:
        scheduler.shutdown()
        print("Scheduler stopped")