"""
Команда для запуска планировщика
"""
import sys
import time
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Запуск планировщика задач'

    def add_arguments(self, parser):
        parser.add_argument(
            '--once',
            action='store_true',
            help='Запустить задачи один раз и завершить',
        )
        parser.add_argument(
            '--job',
            type=str,
            help='Запустить конкретную задачу: monthly или daily',
        )

    def handle(self, *args, **options):
        if options['once']:
            self.run_once(options['job'])
        else:
            self.run_forever()

    def run_once(self, job_name=None):
        try:
            from payment_service.scheduler_jobs import calculate_debts_job, daily_overdue_check_job
            
            self.stdout.write("Running jobs once...")
            
            if job_name == 'monthly' or not job_name:
                self.stdout.write("Running monthly debt calculation...")
                calculate_debts_job()
            
            if job_name == 'daily' or not job_name:
                self.stdout.write("Running daily overdue check...")
                daily_overdue_check_job()
            
            self.stdout.write(self.style.SUCCESS("Jobs completed"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))

    def run_forever(self):
        try:
            from payment_service.scheduler_jobs import start_scheduler
            
            self.stdout.write("Starting scheduler...")
            start_scheduler()
            self.stdout.write(self.style.SUCCESS("Scheduler is running. Press Ctrl+C to stop."))
            
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write("\nScheduler stopped.")
            sys.exit(0)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error starting scheduler: {e}"))