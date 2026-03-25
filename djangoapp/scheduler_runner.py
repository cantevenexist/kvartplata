"""
Скрипт для запуска планировщика в отдельном процессе
"""
import os
import sys
import django

# Настройка Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quicksolve.settings')
django.setup()

from payment_service.scheduler_jobs import start_scheduler

if __name__ == "__main__":
    print("Starting scheduler from standalone script...")
    scheduler = start_scheduler()
    
    if scheduler:
        print("Scheduler is running. Press Ctrl+C to stop.")
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping scheduler...")
            scheduler.shutdown()