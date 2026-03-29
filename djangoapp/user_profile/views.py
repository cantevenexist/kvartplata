from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import TemplateView, ListView
from django.db.models import Q, Sum
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta
from django.http import Http404
from django.http import JsonResponse
from .models import User, UserProfile, Notification
from payment_service.models import Tariff, Charge, Payment, Debt
from housing.models import HousingUnit


class MyProfileView(LoginRequiredMixin, View):
    def get(self, request):
        return redirect('user_profile:profile', username=request.user.username)
    
    
class ProfileView(View):
    template_name = 'profile/profile.html'
    
    def get(self, request, username):
        user = get_object_or_404(User, username=username)
        user_profile = get_object_or_404(UserProfile, user=user)
        
        is_owner = request.user.is_authenticated and request.user == user
        is_staff = request.user.is_staff
        is_superuser = request.user.is_superuser

        # Проверка доступа
        if not is_owner and not is_staff:
            raise Http404('Нет доступа')
        
        if user_profile.user.is_superuser:
            raise Http404('Профиль не существует')

        context = {
            'is_staff': is_staff,
            'user_profile': user_profile,
            'is_owner': is_owner,
            'is_superuser': is_superuser,
        }
        
        return render(request, self.template_name, context)


class UserChargesView(LoginRequiredMixin, ListView):
    """Просмотр начислений пользователя"""
    template_name = 'profile/user_charges.html'
    context_object_name = 'charges'
    paginate_by = 20

    def get_queryset(self):
        owner = self.request.user
        
        if owner.is_superuser or owner.is_staff:
            raise Http404('У пользователя не может быть начислений.')

        # Получаем квартиры пользователя
        user_housings = HousingUnit.objects.filter(owner=self.request.user)
        housing_ids = [housing.id for housing in user_housings]
        
        if not housing_ids:
            return Charge.objects.none()
        
        return Charge.objects.filter(
            housing_id__in=housing_ids
        ).select_related('tariff').order_by('-period', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Добавляем адреса квартир
        charges = context['charges']
        housing_cache = {}
        
        for charge in charges:
            if charge.housing_id not in housing_cache:
                try:
                    unit = HousingUnit.objects.get(id=charge.housing_id)
                    housing_cache[charge.housing_id] = {
                        'address': unit.address,
                        'total_area': unit.total_area,
                    }
                except:
                    housing_cache[charge.housing_id] = {
                        'address': f'Квартира #{charge.housing_id}',
                        'total_area': 0,
                    }
            
            charge.housing_address = housing_cache[charge.housing_id]['address']
            charge.housing_area = housing_cache[charge.housing_id]['total_area']
            charge.remaining = charge.remaining_amount
        
        return context


class UserPaymentsView(LoginRequiredMixin, ListView):
    """Просмотр платежей пользователя"""
    template_name = 'profile/user_payments.html'
    context_object_name = 'payments'
    paginate_by = 20

    def get_queryset(self):
        owner = self.request.user
        
        if owner.is_superuser or owner.is_staff:
            raise Http404('У пользователя не может быть платежей.')

        # Получаем квартиры пользователя
        user_housings = HousingUnit.objects.filter(owner=self.request.user)
        housing_ids = [housing.id for housing in user_housings]
        
        if not housing_ids:
            return Payment.objects.none()
        
        return Payment.objects.filter(
            housing_id__in=housing_ids
        ).order_by('-payment_date', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Добавляем адреса квартир
        payments = context['payments']
        housing_cache = {}
        
        for payment in payments:
            if payment.housing_id not in housing_cache:
                try:
                    unit = HousingUnit.objects.get(id=payment.housing_id)
                    housing_cache[payment.housing_id] = {
                        'address': unit.address,
                    }
                except:
                    housing_cache[payment.housing_id] = {
                        'address': f'Квартира #{payment.housing_id}',
                    }
            
            payment.housing_address = housing_cache[payment.housing_id]['address']
        
        return context


class UserDebtView(LoginRequiredMixin, TemplateView):
    """Просмотр долгов пользователя в личном кабинете"""
    template_name = 'profile/user_debt.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        owner = self.request.user
        
        if owner.is_superuser or owner.is_staff:
            raise Http404('У пользователя не может быть долгов.')

        user_housings = HousingUnit.objects.filter(owner=self.request.user)
        
        debts = []
        total_debt = 0
        
        # Функция для расчета даты оплаты
        def get_due_date(period_date):
            from dateutil.relativedelta import relativedelta
            next_month = period_date + relativedelta(months=1)
            return next_month.replace(day=15)
        
        today = timezone.now().date()
        
        for housing in user_housings:
            # Получаем все неоплаченные начисления для квартиры
            unpaid_charges = Charge.objects.filter(
                housing_id=housing.id,
                is_paid=False
            ).order_by('period')
            
            if not unpaid_charges.exists():
                continue
            
            # Группируем по периодам
            period_totals = {}
            for charge in unpaid_charges:
                period = charge.period
                remaining = charge.remaining_amount
                if remaining > 0:
                    if period not in period_totals:
                        period_totals[period] = Decimal('0')
                    period_totals[period] += remaining
            
            # Проверяем просрочку для каждого периода
            for period, amount in period_totals.items():
                due_date = get_due_date(period)
                is_overdue = today > due_date
                overdue_days = (today - due_date).days if is_overdue else 0
                
                if amount > 0:
                    debts.append({
                        'housing_id': housing.id,
                        'address': housing.address,
                        'period': period,
                        'amount': amount,
                        'due_date': due_date,
                        'is_overdue': is_overdue,
                        'overdue_days': overdue_days,
                    })
                    total_debt += amount
        
        # Сортируем долги: сначала просроченные, потом по дате
        debts.sort(key=lambda x: (not x['is_overdue'], x['period']))
        
        context['debts'] = debts
        context['total_debt'] = total_debt
        context['has_debt'] = len(debts) > 0
        
        return context


class NotificationDetailView(LoginRequiredMixin, View):
    """Получить детали уведомления"""
    
    def get(self, request, notification_id):
        notification = get_object_or_404(Notification, id=notification_id, user=request.user)
        
        return JsonResponse({
            'success': True,
            'notification': {
                'id': notification.id,
                'message': notification.message,
                'level': notification.level,
                'is_read': notification.is_read,
                'created_at': notification.created_at,
                'related_url': notification.related_url or ''
            }
        })

class AllNotificationsView(LoginRequiredMixin, View):
    """Получить все уведомления пользователя"""
    
    def get(self, request):
        notifications = Notification.objects.filter(user=request.user)
        
        notifications_data = []
        for notification in notifications:
            notifications_data.append({
                'id': notification.id,
                'message': notification.message,
                'level': notification.level,
                'is_read': notification.is_read,
                'created_at': notification.created_at,
                'related_url': notification.related_url or ''
            })
        
        return JsonResponse({
            'success': True,
            'notifications': notifications_data
        })

class MarkNotificationReadView(LoginRequiredMixin, View):
    """Пометить уведомление как прочитанное"""
    
    def post(self, request, notification_id):
        # Проверяем, что запрос пришел через AJAX
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Invalid request'})
        
        notification = get_object_or_404(Notification, id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        
        return JsonResponse({'success': True})