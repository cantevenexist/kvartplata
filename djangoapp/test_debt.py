"""
Простой тест для проверки долгов

docker-compose exec web python test_debt.py
"""
import os
import sys
import django
from datetime import datetime, timedelta
from decimal import Decimal

# Настройка Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quicksolve.settings')
django.setup()

from payment_service.debt_calculator import update_all_debts
from payment_service.models import Debt, Charge, Tariff
from housing.models import HousingUnit


def test_debt_calculation():
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ РАСЧЕТА ДОЛГОВ")
    print("=" * 60)
    
    # 1. Создаем тестовую квартиру
    unit, _ = HousingUnit.objects.get_or_create(
        id=9999,
        defaults={
            'address': 'Тестовый адрес, д.1, кв.1',
            'total_area': 50,
        }
    )
    print(f"\n1. Создана тестовая квартира ID: {unit.id}")
    
    # 2. Создаем тариф
    tariff, _ = Tariff.objects.get_or_create(
        name='Тестовый тариф',
        defaults={
            'rate_per_unit': 10,
            'unit': 'm2',
            'is_active': True,
        }
    )
    print(f"2. Тариф: {tariff.name} - {tariff.rate_per_unit} руб./{tariff.get_unit_display()}")
    
    # 3. Создаем начисление за март 2026
    period = datetime(2026, 3, 1).date()
    charge = Charge.objects.create(
        housing_id=unit.id,
        tariff=tariff,
        period=period,
        amount=Decimal('500'),
        original_amount=Decimal('500'),
        paid_amount=Decimal('0'),
        is_paid=False
    )
    print(f"3. Создано начисление: {charge.amount} руб. за {period}")
    
    # 4. Проверяем долги (сегодня реальная дата)
    print(f"\n4. Сегодня: {datetime.now().date()}")
    update_all_debts()
    debts = Debt.objects.filter(housing_id=unit.id)
    if debts.exists():
        print(f"   Долг: {debts.first().total_amount} руб.")
    else:
        print("   Долга нет")
    
    # 5. Имитируем 16 апреля 2026
    print("\n5. Имитация 16 апреля 2026...")
    # Временно меняем дату (просто выводим что должно быть)
    due_date = datetime(2026, 4, 15).date()
    fake_today = datetime(2026, 4, 16).date()
    print(f"   Дата оплаты до: {due_date}")
    print(f"   Сегодня: {fake_today}")
    print(f"   Просрочено: {fake_today > due_date}")
    print(f"   Долг должен быть: {charge.amount} руб.")
    
    # 6. Очистка
    print("\n6. Очистка тестовых данных...")
    Charge.objects.filter(id=charge.id).delete()
    Debt.objects.filter(housing_id=unit.id).delete()
    HousingUnit.objects.filter(id=unit.id).delete()
    print("   Готово!")
    
    print("\n" + "=" * 60)
    print("ТЕСТ ЗАВЕРШЕН")
    print("=" * 60)


if __name__ == "__main__":
    test_debt_calculation()