"""
Модуль для автоматического расчета задолженностей
"""
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

from .models import Charge, Payment, Debt
from housing.models import HousingUnit

logger = logging.getLogger(__name__)


def get_due_date_for_period(period_date):
    """
    Возвращает дату, до которой нужно оплатить начисление
    Например: март 2024 -> 15 апреля 2024
    Декабрь 2024 -> 15 января 2025
    """
    # Добавляем 1 месяц с помощью dateutil.relativedelta
    next_month = period_date + relativedelta(months=1)
    # Устанавливаем день 15
    due_date = next_month.replace(day=15)
    return due_date


def is_period_overdue(period_date):
    """
    Проверяет, наступила ли дата оплаты для периода
    """
    today = timezone.now().date()
    due_date = get_due_date_for_period(period_date)
    return today > due_date


def calculate_housing_debt(housing_id):
    """
    Рассчитывает общий долг для квартиры
    Учитываются только периоды, у которых наступила дата оплаты
    Возвращает: (total_debt, last_period)
    """
    charges = Charge.objects.filter(housing_id=housing_id)
    
    if not charges.exists():
        return Decimal('0'), None
    
    total_debt = Decimal('0')
    last_period = None
    today = timezone.now().date()
    
    periods = charges.values_list('period', flat=True).distinct().order_by('period')
    
    for period in periods:
        # Проверяем, наступила ли дата оплаты для этого периода
        due_date = get_due_date_for_period(period)
        
        # Если дата оплаты еще не наступила, пропускаем этот период
        if today <= due_date:
            continue
        
        period_charges = charges.filter(period=period)
        
        total_charged = period_charges.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        total_paid = period_charges.aggregate(total=Sum('paid_amount'))['total'] or Decimal('0')
        unpaid = total_charged - total_paid
        
        # Получаем платежи за этот период (исправлено!)
        period_start = period
        period_end = period + relativedelta(months=1) - timedelta(days=1)
        
        period_payments = Payment.objects.filter(
            housing_id=housing_id,
            payment_date__date__gte=period_start,
            payment_date__date__lte=period_end
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        period_debt = max(unpaid - period_payments, Decimal('0'))
        
        if period_debt > 0:
            total_debt += period_debt
            last_period = period
    
    return total_debt, last_period


def update_all_debts():
    """Обновляет долги для всех квартир"""
    print(f"[{datetime.now()}] Starting debts calculation...")
    
    units = HousingUnit.objects.all()
    results = {
        'total_units': units.count(),
        'updated': 0,
        'created': 0,
        'deleted': 0,
        'total_debt': Decimal('0'),
        'errors': 0
    }
    
    for unit in units:
        try:
            total_debt, last_period = calculate_housing_debt(unit.id)
            
            if total_debt > 0:
                debt, created = Debt.objects.update_or_create(
                    housing_id=unit.id,
                    defaults={
                        'total_amount': total_debt,
                    }
                )
                results['total_debt'] += total_debt
                if created:
                    results['created'] += 1
                else:
                    results['updated'] += 1
            else:
                deleted, _ = Debt.objects.filter(housing_id=unit.id).delete()
                if deleted:
                    results['deleted'] += 1
                    
        except Exception as e:
            print(f"Error processing housing {unit.id}: {e}")
            results['errors'] += 1
    
    print(f"[{datetime.now()}] Debts calculation completed. Results: {results}")
    return results


def update_single_debt(housing_id):
    """Обновляет долг для конкретной квартиры"""
    try:
        total_debt, last_period = calculate_housing_debt(housing_id)
        
        if total_debt > 0:
            debt, created = Debt.objects.update_or_create(
                housing_id=housing_id,
                defaults={
                    'total_amount': total_debt,
                }
            )
            return debt
        else:
            Debt.objects.filter(housing_id=housing_id).delete()
            return None
            
    except Exception as e:
        print(f"Error updating debt for housing {housing_id}: {e}")
        raise


def get_debt_statistics():
    """Получает статистику по долгам (уникальные должники)"""
    from django.db.models import Sum, Avg
    
    # Получаем всех уникальных должников
    debtors = Debt.objects.filter(total_amount__gt=0).values('housing_id').distinct()
    total_debtors = debtors.count()
    
    # Общая сумма долга
    total_debt = Debt.objects.filter(total_amount__gt=0).aggregate(
        total=Sum('total_amount')
    )['total'] or Decimal('0')

    return {
        'total_debtors': total_debtors,
        'total_debt': total_debt,
    }