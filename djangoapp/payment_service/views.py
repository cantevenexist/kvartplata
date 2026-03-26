from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views import View
from django.contrib import messages
from django.utils import timezone
from django.http import Http404
from .models import Tariff
from datetime import timedelta
from django.utils.formats import date_format

class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser
    
    def handle_no_permission(self):
        raise Http404('Нет доступа')

class TariffListView(LoginRequiredMixin, View):
    def get(self, request):
        if not (self.request.user.is_superuser or self.request.user.is_staff):
            raise Http404('Нет доступа')

        tariffs = Tariff.objects.all()
        return render(request, 'payment_service/tariff_list.html', {
            'tariffs': tariffs,
            'now': timezone.now().date(),
        })

class TariffCreateView(LoginRequiredMixin, AdminRequiredMixin, View):
    def get(self, request):
        return render(request, 'payment_service/tariff_form.html', {
            'unit_choices': Tariff.UNIT_CHOICES,
            'current_status': 'active',  # По умолчанию активен
        })
    
    def post(self, request):
        name = request.POST.get('name')
        rate_per_unit = request.POST.get('rate_per_unit').replace(',', '.')
        unit = request.POST.get('unit')
        status = request.POST.get('status')
        valid_to = request.POST.get('valid_to') or None
        
        if valid_to:
            valid_to = timezone.datetime.strptime(valid_to, '%Y-%m-%d').date()
        
        Tariff.objects.create(
            name=name,
            rate_per_unit=rate_per_unit,
            unit=unit,
            valid_to=valid_to,
            is_active=(status == 'active')  # Только active = True, остальное False
        )
        
        messages.success(request, f'Тариф "{name}" создан')
        return redirect('payment_service:tariff_list')

class TariffUpdateView(LoginRequiredMixin, AdminRequiredMixin, View):
    def get(self, request, tariff_id):
        tariff = get_object_or_404(Tariff, id=tariff_id)
        
        # Определяем текущий статус
        current_status = 'archived' if not tariff.is_active else 'active'
        
        return render(request, 'payment_service/tariff_form.html', {
            'tariff': tariff,
            'current_status': current_status,
            'unit_choices': Tariff.UNIT_CHOICES,
            'now': timezone.now().date(),  # Для предупреждения о просрочке
        })
    
    def post(self, request, tariff_id):
        tariff = get_object_or_404(Tariff, id=tariff_id)
        
        name = request.POST.get('name')
        rate_per_unit = request.POST.get('rate_per_unit').replace(',', '.')
        unit = request.POST.get('unit')
        status = request.POST.get('status')
        valid_to = request.POST.get('valid_to') or None
        
        if valid_to:
            valid_to = timezone.datetime.strptime(valid_to, '%Y-%m-%d').date()
        
        tariff.name = name
        tariff.rate_per_unit = rate_per_unit
        tariff.unit = unit
        tariff.valid_to = valid_to
        tariff.is_active = (status == 'active')
        tariff.save()
        
        messages.success(request, f'Тариф "{tariff.name}" обновлен')
        return redirect('payment_service:tariff_list')

class TariffArchiveView(LoginRequiredMixin, AdminRequiredMixin, View):
    def post(self, request, tariff_id):
        tariff = get_object_or_404(Tariff, id=tariff_id)
        tariff.is_active = False
        tariff.save()
        messages.success(request, f'Тариф "{tariff.name}" в архиве')
        return redirect('payment_service:tariff_list')

class TariffRestoreView(LoginRequiredMixin, AdminRequiredMixin, View):
    def post(self, request, tariff_id):
        tariff = get_object_or_404(Tariff, id=tariff_id)
        tariff.is_active = True
        tariff.save()
        messages.success(request, f'Тариф "{tariff.name}" восстановлен')
        return redirect('payment_service:tariff_list')

from django.views.generic import TemplateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Q
from django.http import Http404, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from decimal import Decimal
from datetime import datetime
import json

from .models import Tariff, Charge, Payment, Debt


class BuhRequiredMixin(LoginRequiredMixin):
    """Mixin для проверки прав бухгалтера"""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.is_staff and not request.user.is_superuser):
            raise Http404('Нет доступа')
        return super().dispatch(request, *args, **kwargs)

def get_due_date_for_period(period_date):
    """
    Возвращает дату, до которой нужно оплатить начисление
    Например: март 2024 -> 15 апреля 2024
    """
    from datetime import timedelta
    next_month = period_date.replace(day=1) + timedelta(days=32)
    due_date = next_month.replace(day=15)
    return due_date

class ChargeCreateView(BuhRequiredMixin, TemplateView):
    """
    Страница создания начислений
    """
    template_name = 'payment_service/charge_create.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tariffs'] = Tariff.objects.filter(is_active=True)
        context['today'] = timezone.now().date()
        
        # Поиск квартир
        search_query = self.request.GET.get('search', '')
        context['search_query'] = search_query
        
        if search_query:
            from housing.models import HousingUnit
            units = HousingUnit.objects.filter(
                Q(address__icontains=search_query) |
                Q(owner__username__icontains=search_query) |
                Q(owner__email__icontains=search_query) |
                Q(owner__profile__full_name__icontains=search_query) |
                Q(owner__profile__phone_number__icontains=search_query)
            ).distinct()[:20]
            
            search_results = []
            for unit in units:
                try:
                    user = unit.owner
                    profile = user.profile
                    search_results.append({
                        'id': unit.id,
                        'address': unit.address,
                        'total_area': unit.total_area,
                        'owner_name': profile.full_name or 'Не указано',
                        'phone': profile.phone_number or 'Не указан',
                        'email': user.email,
                        'prepayment': getattr(unit, 'prepayment', 0),
                    })
                except:
                    search_results.append({
                        'id': unit.id,
                        'address': unit.address,
                        'total_area': unit.total_area,
                        'owner_name': 'Нет владельца',
                        'phone': '—',
                        'email': '—',
                        'prepayment': getattr(unit, 'prepayment', 0),
                    })
            context['search_results'] = search_results
        
        # Если выбрана квартира
        housing_id = self.request.GET.get('housing_id')
        if housing_id:
            try:
                from housing.models import HousingUnit
                housing = HousingUnit.objects.get(id=housing_id)
                context['selected_housing'] = housing
                context['housing_id'] = housing_id
                context['default_consumption'] = housing.total_area
                context['prepayment'] = getattr(housing, 'prepayment', 0)
            except:
                pass
        
        return context

    def post(self, request, *args, **kwargs):
        housing_id = request.POST.get('housing_id')
        tariff_id = request.POST.get('tariff_id')
        period = request.POST.get('period')
        consumption = request.POST.get('consumption')

        if not all([housing_id, tariff_id, period, consumption]):
            messages.error(request, 'Заполните все поля')
            return redirect(request.path)

        try:
            housing_id = int(housing_id)
            tariff = Tariff.objects.get(id=tariff_id, is_active=True)
            period_date = datetime.strptime(period, '%Y-%m').date()
            consumption_value = Decimal(consumption)

            if consumption_value <= 0:
                messages.error(request, 'Количество должно быть больше 0')
                return redirect(f'{request.path}?housing_id={housing_id}')

            if tariff.valid_to and tariff.valid_to < period_date:
                messages.error(request, f'Тариф "{tariff.name}" не действует в выбранный период')
                return redirect(f'{request.path}?housing_id={housing_id}')

            amount = (consumption_value * tariff.rate_per_unit).quantize(Decimal('0.01'))
            
            from housing.models import HousingUnit
            unit = HousingUnit.objects.get(id=housing_id)
            
            # Проверяем, существует ли уже начисление за этот период с этим тарифом
            existing_charge = Charge.objects.filter(
                housing_id=housing_id,
                tariff=tariff,
                period=period_date
            ).first()
            
            if existing_charge:
                from django.utils.formats import date_format
                messages.error(
                    request, 
                    f'Начисление за {date_format(period_date, "F Y")} с тарифом "{tariff.name}" уже существует. '
                    f'Сумма: {existing_charge.amount} руб.'
                )
                return redirect(f'{request.path}?housing_id={housing_id}')
            
            with transaction.atomic():
                # Проверяем, есть ли аванс
                if unit.prepayment > 0:
                    if unit.prepayment >= amount:
                        # Аванс покрывает всю сумму
                        unit.prepayment -= amount
                        unit.save()
                        
                        # Создаем начисление с пометкой "оплачено авансом"
                        charge = Charge.objects.create(
                            housing_id=housing_id,
                            tariff=tariff,
                            period=period_date,
                            amount=amount,
                            original_amount=amount,
                            paid_amount=amount,
                            is_paid=True
                        )
                        messages.success(request, f'Начисление создано и оплачено авансом. Остаток аванса: {unit.prepayment} руб.')
                        
                    else:
                        # Аванс покрывает часть суммы
                        remaining = amount - unit.prepayment
                        
                        # Создаем начисление с частичной оплатой из аванса
                        charge = Charge.objects.create(
                            housing_id=housing_id,
                            tariff=tariff,
                            period=period_date,
                            amount=amount,
                            original_amount=amount,
                            paid_amount=unit.prepayment,
                            is_paid=False
                        )
                        
                        messages.info(request, 
                            f'Начисление создано. Списано {unit.prepayment} руб. из аванса. '
                            f'Остаток к оплате: {remaining} руб.'
                        )
                        
                        # Обнуляем аванс
                        unit.prepayment = 0
                        unit.save()
                else:
                    # Обычное создание начисления - без аванса
                    charge = Charge.objects.create(
                        housing_id=housing_id,
                        tariff=tariff,
                        period=period_date,
                        amount=amount,
                        original_amount=amount,
                        paid_amount=0,
                        is_paid=False
                    )
                    
                    messages.success(request, f'Начисление создано: {amount} руб.')

                # Обновляем долги для всех периодов
                self.update_debt_for_periods(housing_id)

            return redirect('payment_service:charge_list')

        except Exception as e:
            messages.error(request, f'Ошибка: {e}')
            return redirect(f'{request.path}?housing_id={housing_id}')

    def get_due_date_for_period(self, period_date):
        """Возвращает дату оплаты для периода (15 число следующего месяца)"""
        from dateutil.relativedelta import relativedelta
        next_month = period_date + relativedelta(months=1)
        due_date = next_month.replace(day=15)
        return due_date

    def update_debt_for_periods(self, housing_id):
        """
        Обновляет задолженность для каждого просроченного периода отдельно
        Суммирует все тарифы за период (включая частично оплаченные)
        """
        from housing.models import HousingUnit
        from dateutil.relativedelta import relativedelta
        
        today = timezone.now().date()
        
        # Получаем ВСЕ начисления (не только is_paid=False, но и частично оплаченные)
        # Нам нужны все начисления, у которых есть остаток (amount - paid_amount > 0)
        all_charges = Charge.objects.filter(
            housing_id=housing_id
        ).exclude(
            is_paid=True  # Исключаем полностью оплаченные
        ).order_by('period')
        
        # Получаем аванс квартиры
        try:
            unit = HousingUnit.objects.get(id=housing_id)
            prepayment = getattr(unit, 'prepayment', 0)
        except:
            prepayment = 0
        
        # Группируем начисления по периодам и суммируем остатки
        period_totals = {}
        for charge in all_charges:
            period = charge.period
            remaining = charge.remaining_amount  # amount - paid_amount
            if remaining > 0:
                if period not in period_totals:
                    period_totals[period] = Decimal('0')
                period_totals[period] += remaining
        
        # Словарь для хранения долгов по периодам
        period_debts = {}
        remaining_prepayment = prepayment
        
        # Проходим по периодам от старых к новым
        for period in sorted(period_totals.keys()):
            due_date = self.get_due_date_for_period(period)
            period_debt = period_totals[period]
            
            # Если есть аванс, сначала списываем его с просроченных периодов
            if remaining_prepayment > 0 and today > due_date:
                if remaining_prepayment >= period_debt:
                    period_debt = 0
                    remaining_prepayment -= period_debt
                else:
                    period_debt -= remaining_prepayment
                    remaining_prepayment = 0
            
            # Сохраняем долг только для просроченных периодов
            if today > due_date and period_debt > 0:
                period_debts[period] = period_debt
        
        # Обновляем записи в таблице Debt
        # Удаляем все старые записи для этой квартиры
        Debt.objects.filter(housing_id=housing_id).delete()
        
        # Создаем новые записи для каждого периода с долгом
        for period, debt_amount in period_debts.items():
            Debt.objects.create(
                housing_id=housing_id,
                period=period,
                total_amount=debt_amount
            )
        
        # Обновляем остаток аванса в квартире (если он изменился)
        if remaining_prepayment != prepayment:
            unit.prepayment = remaining_prepayment
            unit.save()

class DebtListView(BuhRequiredMixin, ListView):
    """Список задолженностей для бухгалтера"""
    model = Debt
    template_name = 'payment_service/debt_list.html'
    context_object_name = 'debts'
    paginate_by = 50

    def get_queryset(self):
        queryset = super().get_queryset().filter(total_amount__gt=0)
        
        search_query = self.request.GET.get('search', '')
        if search_query:
            from housing.models import HousingUnit
            units = HousingUnit.objects.filter(
                Q(address__icontains=search_query) |
                Q(owner__profile__full_name__icontains=search_query) |
                Q(owner__username__icontains=search_query)
            ).distinct()
            
            if units.exists():
                housing_ids = [unit.id for unit in units]
                queryset = queryset.filter(housing_id__in=housing_ids)
            else:
                queryset = queryset.none()
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        
        from housing.models import HousingUnit
        
        debts = context['debts']
        housing_ids = [debt.housing_id for debt in debts]
        
        if housing_ids:
            units = HousingUnit.objects.filter(id__in=housing_ids).select_related('owner', 'owner__profile')
            housing_data = {}
            
            for unit in units:
                owner_name = 'Нет владельца'
                if unit.owner:
                    try:
                        owner_name = unit.owner.profile.full_name or unit.owner.username
                    except:
                        owner_name = unit.owner.username
                
                housing_data[unit.id] = {
                    'address': unit.address,
                    'owner_name': owner_name,
                }
            
            for debt in debts:
                if debt.housing_id in housing_data:
                    debt.housing_address = housing_data[debt.housing_id]['address']
                    debt.owner_name = housing_data[debt.housing_id]['owner_name']
                else:
                    debt.housing_address = f'Жилье #{debt.housing_id}'
                    debt.owner_name = '—'
        
        return context


class ChargeListView(BuhRequiredMixin, ListView):
    """Список начислений"""
    model = Charge
    template_name = 'payment_service/charge_list.html'
    context_object_name = 'charges'
    paginate_by = 50

    def get_queryset(self):
        queryset = super().get_queryset().select_related('tariff')
        
        # Поиск по адресу или владельцу
        search_query = self.request.GET.get('search', '')
        if search_query:
            from housing.models import HousingUnit
            units = HousingUnit.objects.filter(
                Q(address__icontains=search_query) |
                Q(owner__profile__full_name__icontains=search_query) |
                Q(owner__username__icontains=search_query)
            )
            
            if units.exists():
                housing_ids = [unit.id for unit in units]
                queryset = queryset.filter(housing_id__in=housing_ids)
            else:
                queryset = queryset.none()
        
        return queryset.order_by('-period', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        
        from housing.models import HousingUnit
        
        for charge in context['charges']:
            try:
                unit = HousingUnit.objects.get(id=charge.housing_id)
                charge.housing_address = unit.address
                if unit.owner:
                    try:
                        charge.owner_name = unit.owner.profile.full_name or unit.owner.username
                    except:
                        charge.owner_name = unit.owner.username
                else:
                    charge.owner_name = 'Нет владельца'
            except HousingUnit.DoesNotExist:
                charge.housing_address = f'Жилье #{charge.housing_id}'
                charge.owner_name = '—'
        
        return context


class PaymentListView(BuhRequiredMixin, ListView):
    """Список платежей"""
    model = Payment
    template_name = 'payment_service/payment_list.html'
    context_object_name = 'payments'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Поиск по адресу или владельцу (как в PaymentCreateView)
        search_query = self.request.GET.get('search', '')
        if search_query:
            from housing.models import HousingUnit
            # Находим квартиры по поисковому запросу
            units = HousingUnit.objects.filter(
                Q(address__icontains=search_query) |
                Q(owner__profile__full_name__icontains=search_query) |
                Q(owner__username__icontains=search_query)
            ).distinct()
            
            if units.exists():
                housing_ids = [unit.id for unit in units]
                queryset = queryset.filter(housing_id__in=housing_ids)
            else:
                # Если квартиры не найдены, возвращаем пустой queryset
                queryset = queryset.none()
        
        # Фильтр по дате (оставляем для удобства)
        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(payment_date__date__gte=date_from)
        
        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(payment_date__date__lte=date_to)
        
        return queryset.order_by('-payment_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['filter_date_from'] = self.request.GET.get('date_from', '')
        context['filter_date_to'] = self.request.GET.get('date_to', '')
        
        # Добавляем информацию о квартирах для каждого платежа
        from housing.models import HousingUnit
        
        payments = context['payments']
        housing_cache = {}
        
        # Собираем все ID квартир
        housing_ids = set()
        for payment in payments:
            housing_ids.add(payment.housing_id)
        
        # Получаем данные квартир одним запросом
        if housing_ids:
            units = HousingUnit.objects.filter(id__in=housing_ids).select_related('owner', 'owner__profile')
            
            for unit in units:
                owner_name = 'Нет владельца'
                if unit.owner:
                    try:
                        owner_name = unit.owner.profile.full_name or unit.owner.username
                    except:
                        owner_name = unit.owner.username
                
                housing_cache[unit.id] = {
                    'address': unit.address,
                    'owner_name': owner_name,
                }
        
        # Добавляем данные к каждому платежу
        for payment in payments:
            if payment.housing_id in housing_cache:
                payment.housing_address = housing_cache[payment.housing_id]['address']
                payment.owner_name = housing_cache[payment.housing_id]['owner_name']
            else:
                payment.housing_address = f'Жилье #{payment.housing_id}'
                payment.owner_name = '—'
        
        return context


@csrf_exempt
@require_POST
def api_register_payment(request):
    """
    API endpoint для регистрации платежа от банка
    """
    try:
        data = json.loads(request.body)
        
        required_fields = ['housing_id', 'amount', 'payment_method']
        for field in required_fields:
            if field not in data:
                return JsonResponse({
                    'success': False,
                    'error': f'Отсутствует обязательное поле: {field}'
                }, status=400)
        
        payment_date = None
        if data.get('payment_date'):
            try:
                payment_date = datetime.strptime(data['payment_date'], '%Y-%m-%d %H:%M')
            except:
                return JsonResponse({
                    'success': False,
                    'error': 'Неверный формат даты. Используйте YYYY-MM-DD HH:MM'
                }, status=400)
        
        success, message = register_payment(
            housing_id=int(data['housing_id']),
            amount=Decimal(str(data['amount'])),
            payment_method=data['payment_method'],
            payment_date=payment_date,
            description=data.get('description', f"API платеж {data.get('transaction_id', '')}"),
            transaction_id=data.get('transaction_id')
        )
        
        if success:
            return JsonResponse({
                'success': True,
                'message': message,
                'payment_id': message.split('#')[1].split()[0] if '#' in message else None
            })
        else:
            return JsonResponse({
                'success': False,
                'error': message
            }, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Неверный JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def register_payment(housing_id, amount, payment_method, payment_date=None, 
                     description='', created_by=None, transaction_id=None):
    """
    Общая функция регистрации платежа
    """
    try:
        with transaction.atomic():
            if amount <= 0:
                return False, 'Сумма платежа должна быть больше 0'
            
            payment = Payment.objects.create(
                housing_id=housing_id,
                amount=amount,
                payment_method=payment_method,
                payment_date=payment_date or timezone.now(),
                description=description
            )
            
            unpaid_charges = Charge.objects.filter(
                housing_id=housing_id,
                is_paid=False
            ).order_by('period')
            
            remaining_amount = amount
            
            for charge in unpaid_charges:
                if remaining_amount <= 0:
                    break
                
                if charge.amount <= remaining_amount:
                    charge.is_paid = True
                    charge.save()
                    remaining_amount -= charge.amount
            
            # Обновляем задолженность
            total_charges = Charge.objects.filter(
                housing_id=housing_id,
                is_paid=False
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            
            total_payments = Payment.objects.filter(
                housing_id=housing_id
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            
            debt_amount = max(total_charges - total_payments, Decimal('0'))
            
            last_charge = Charge.objects.filter(housing_id=housing_id).order_by('-period').first()
            if last_charge:
                Debt.objects.update_or_create(
                    housing_id=housing_id,
                    period=last_charge.period,
                    defaults={'total_amount': debt_amount}
                )
            
            return True, f'Платеж #{payment.id} успешно зарегистрирован на сумму {amount} руб.'
            
    except Exception as e:
        return False, f'Ошибка регистрации платежа: {e}'


from .debt_calculator import get_debt_statistics, update_single_debt


class BuhRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.is_staff and not request.user.is_superuser):
            raise Http404('Нет доступа')
        return super().dispatch(request, *args, **kwargs)


class DebtListView(BuhRequiredMixin, ListView):
    """Список задолженностей для бухгалтера"""
    model = Debt
    template_name = 'payment_service/debt_list.html'
    context_object_name = 'debts'
    paginate_by = 50

    def get_queryset(self):
        queryset = super().get_queryset().filter(total_amount__gt=0)
        
        search_query = self.request.GET.get('search', '')
        if search_query:
            from housing.models import HousingUnit
            units = HousingUnit.objects.filter(
                Q(address__icontains=search_query) |
                Q(owner__profile__full_name__icontains=search_query) |
                Q(owner__username__icontains=search_query)
            ).distinct()
            
            if units.exists():
                housing_ids = [unit.id for unit in units]
                queryset = queryset.filter(housing_id__in=housing_ids)
            else:
                queryset = queryset.none()
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['statistics'] = get_debt_statistics()
        
        from housing.models import HousingUnit
        
        debts = context['debts']
        housing_ids = [debt.housing_id for debt in debts]
        
        if housing_ids:
            units = HousingUnit.objects.filter(id__in=housing_ids).select_related('owner', 'owner__profile')
            housing_data = {}
            
            for unit in units:
                owner_name = 'Нет владельца'
                if unit.owner:
                    try:
                        owner_name = unit.owner.profile.full_name or unit.owner.username
                    except:
                        owner_name = unit.owner.username
                
                housing_data[unit.id] = {
                    'address': unit.address,
                    'owner_name': owner_name,
                }
            
            for debt in debts:
                if debt.housing_id in housing_data:
                    debt.housing_address = housing_data[debt.housing_id]['address']
                    debt.owner_name = housing_data[debt.housing_id]['owner_name']
                else:
                    debt.housing_address = f'Жилье #{debt.housing_id}'
                    debt.owner_name = '—'
        
        return context


class PaymentCreateView(BuhRequiredMixin, TemplateView):
    """
    Страница регистрации оплаты
    """
    template_name = 'payment_service/payment_create.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['payment_methods'] = Payment.PAYMENT_METHODS
        context['today'] = timezone.now()
        
        # Поиск квартиры
        search_query = self.request.GET.get('search', '')
        context['search_query'] = search_query
        
        if search_query:
            from housing.models import HousingUnit
            units = HousingUnit.objects.filter(
                Q(address__icontains=search_query) |
                Q(owner__profile__full_name__icontains=search_query) |
                Q(owner__username__icontains=search_query)
            ).distinct()[:20]
            
            search_results = []
            for unit in units:
                # Считаем реальный долг (только просроченные, суммируем по всем тарифам)
                today = timezone.now().date()
                total_debt = Decimal('0')
                
                # Получаем все начисления с остатком
                all_charges = Charge.objects.filter(
                    housing_id=unit.id
                ).exclude(
                    is_paid=True
                ).order_by('period')
                
                # Группируем по периодам и суммируем остатки
                period_totals = {}
                for charge in all_charges:
                    remaining = charge.remaining_amount
                    if remaining > 0:
                        period = charge.period
                        if period not in period_totals:
                            period_totals[period] = Decimal('0')
                        period_totals[period] += remaining
                
                # Считаем долг только для просроченных периодов
                for period, amount in period_totals.items():
                    due_date = self.get_due_date_for_period(period)
                    if today > due_date:
                        total_debt += amount
                
                owner_name = 'Нет владельца'
                if unit.owner:
                    try:
                        owner_name = unit.owner.profile.full_name or unit.owner.username
                    except:
                        owner_name = unit.owner.username
                
                search_results.append({
                    'id': unit.id,
                    'address': unit.address,
                    'owner_name': owner_name,
                    'total_debt': total_debt,
                    'prepayment': getattr(unit, 'prepayment', 0),
                })
            context['search_results'] = search_results
        
        # Если выбрана квартира
        housing_id = self.request.GET.get('housing_id')
        if housing_id:
            try:
                from housing.models import HousingUnit
                unit = HousingUnit.objects.get(id=housing_id)
                context['selected_housing'] = unit
                context['housing_id'] = housing_id
                
                # Получаем все начисления с остатком
                all_charges = Charge.objects.filter(
                    housing_id=housing_id
                ).exclude(
                    is_paid=True
                ).select_related('tariff').order_by('period')
                
                today = timezone.now().date()
                for charge in all_charges:
                    charge.remaining = charge.remaining_amount
                    due_date = self.get_due_date_for_period(charge.period)
                    charge.is_overdue = today > due_date
                
                context['unpaid_charges'] = all_charges
                context['prepayment'] = getattr(unit, 'prepayment', 0)
                
                # Считаем общий долг (суммируем по всем тарифам за просроченные периоды)
                period_totals = {}
                for charge in all_charges:
                    remaining = charge.remaining_amount
                    if remaining > 0:
                        period = charge.period
                        if period not in period_totals:
                            period_totals[period] = Decimal('0')
                        period_totals[period] += remaining
                
                total_debt = Decimal('0')
                for period, amount in period_totals.items():
                    due_date = self.get_due_date_for_period(period)
                    if today > due_date:
                        total_debt += amount
                
                context['total_debt'] = total_debt
                
            except Exception as e:
                print(f"Error: {e}")
        
        return context
    
    def get_due_date_for_period(self, period_date):
        """Возвращает дату оплаты для периода (15 число следующего месяца)"""
        from dateutil.relativedelta import relativedelta
        next_month = period_date + relativedelta(months=1)
        due_date = next_month.replace(day=15)
        return due_date
    
    def post(self, request, *args, **kwargs):
        housing_id = request.POST.get('housing_id')
        amount = request.POST.get('amount')
        payment_method = request.POST.get('payment_method')
        payment_date = request.POST.get('payment_date')
        description = request.POST.get('description', '')
        
        if not all([housing_id, amount, payment_method, payment_date]):
            messages.error(request, 'Заполните все обязательные поля')
            return redirect(f'{request.path}?housing_id={housing_id}')
        
        try:
            housing_id = int(housing_id)
            amount = Decimal(amount)
            
            if amount <= 0:
                messages.error(request, 'Сумма должна быть больше 0')
                return redirect(f'{request.path}?housing_id={housing_id}')
            
            with transaction.atomic():
                from housing.models import HousingUnit
                unit = HousingUnit.objects.get(id=housing_id)
                
                # Создаем платеж
                payment = Payment.objects.create(
                    housing_id=housing_id,
                    amount=amount,
                    payment_method=payment_method,
                    payment_date=datetime.strptime(payment_date, '%Y-%m-%dT%H:%M'),
                    description=description
                )
                
                # Получаем ВСЕ начисления с остатком, сортируем от старых к новым
                unpaid_charges = Charge.objects.filter(
                    housing_id=housing_id
                ).exclude(
                    is_paid=True
                ).order_by('period', 'id')
                
                remaining_amount = amount
                prepayment = getattr(unit, 'prepayment', 0)
                
                # Сначала используем аванс если он есть
                if prepayment > 0:
                    for charge in unpaid_charges:
                        if prepayment <= 0:
                            break
                        
                        remaining = charge.remaining_amount
                        
                        if prepayment >= remaining:
                            charge.paid_amount += remaining
                            if charge.paid_amount >= charge.amount:
                                charge.is_paid = True
                            charge.save()
                            prepayment -= remaining
                            messages.info(request, f'Начисление за {charge.period.strftime("%B %Y")} ({charge.tariff.name}) оплачено авансом')
                        else:
                            charge.paid_amount += prepayment
                            charge.save()
                            messages.info(request, f'Начисление за {charge.period.strftime("%B %Y")} ({charge.tariff.name}) частично оплачено авансом')
                            prepayment = 0
                            break
                    
                    # Сохраняем остаток аванса
                    unit.prepayment = prepayment
                    unit.save()
                
                # Теперь обрабатываем текущий платеж
                for charge in unpaid_charges:
                    if remaining_amount <= 0:
                        break
                    
                    remaining = charge.remaining_amount
                    
                    if remaining_amount >= remaining:
                        # Полная оплата начисления
                        charge.paid_amount += remaining
                        if charge.paid_amount >= charge.amount:
                            charge.is_paid = True
                        charge.save()
                        remaining_amount -= remaining
                        messages.info(request, f'Начисление за {charge.period.strftime("%B %Y")} ({charge.tariff.name}) полностью оплачено')
                    else:
                        # Частичная оплата
                        charge.paid_amount += remaining_amount
                        charge.save()
                        messages.info(request, f'Начисление за {charge.period.strftime("%B %Y")} ({charge.tariff.name}) частично оплачено. Остаток: {charge.remaining_amount} руб.')
                        remaining_amount = 0
                
                # Если остались деньги (переплата) - добавляем в аванс квартиры
                if remaining_amount > 0:
                    unit.prepayment = getattr(unit, 'prepayment', 0) + remaining_amount
                    unit.save()
                    messages.success(request, 
                        f'Переплата {remaining_amount} руб. добавлена к авансу. '
                        f'Текущий аванс: {unit.prepayment} руб.'
                    )
                
                # Обновляем долги для каждого просроченного периода отдельно
                self.update_debt_for_periods(housing_id)
                
                messages.success(request, f'Платеж #{payment.id} успешно зарегистрирован на сумму {amount} руб.')
                return redirect('payment_service:payment_list')
                
        except Exception as e:
            messages.error(request, f'Ошибка: {e}')
            return redirect(f'{request.path}?housing_id={housing_id}')
    
    def update_debt_for_periods(self, housing_id):
        """
        Обновляет задолженность для каждого просроченного периода отдельно
        Суммирует все тарифы за период (включая частично оплаченные)
        """
        from housing.models import HousingUnit
        
        today = timezone.now().date()
        
        # Получаем ВСЕ начисления с остатком (исключаем полностью оплаченные)
        all_charges = Charge.objects.filter(
            housing_id=housing_id
        ).exclude(
            is_paid=True
        ).order_by('period')
        
        # Получаем аванс квартиры
        try:
            unit = HousingUnit.objects.get(id=housing_id)
            prepayment = getattr(unit, 'prepayment', 0)
        except:
            prepayment = 0
        
        # Группируем начисления по периодам и суммируем остатки
        period_totals = {}
        for charge in all_charges:
            period = charge.period
            remaining = charge.remaining_amount
            if remaining > 0:
                if period not in period_totals:
                    period_totals[period] = Decimal('0')
                period_totals[period] += remaining
        
        # Словарь для хранения долгов по периодам
        period_debts = {}
        remaining_prepayment = prepayment
        
        # Проходим по периодам от старых к новым
        for period in sorted(period_totals.keys()):
            due_date = self.get_due_date_for_period(period)
            period_debt = period_totals[period]
            
            # Если есть аванс, сначала списываем его с просроченных периодов
            if remaining_prepayment > 0 and today > due_date:
                if remaining_prepayment >= period_debt:
                    period_debt = 0
                    remaining_prepayment -= period_debt
                else:
                    period_debt -= remaining_prepayment
                    remaining_prepayment = 0
            
            # Сохраняем долг только для просроченных периодов
            if today > due_date and period_debt > 0:
                period_debts[period] = period_debt
        
        # Обновляем записи в таблице Debt
        Debt.objects.filter(housing_id=housing_id).delete()
        
        # Создаем новые записи для каждого периода с долгом
        for period, debt_amount in period_debts.items():
            Debt.objects.create(
                housing_id=housing_id,
                period=period,
                total_amount=debt_amount
            )
        
        # Обновляем остаток аванса в квартире (если он изменился)
        if remaining_prepayment != prepayment:
            unit.prepayment = remaining_prepayment
            unit.save()