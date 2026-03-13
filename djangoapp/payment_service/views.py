# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views import View
from django.contrib import messages
from django.utils import timezone
from django.http import Http404
from .models import Tariff

class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser
    
    def handle_no_permission(self):
        raise Http404('Нет доступа')

class TariffListView(LoginRequiredMixin, AdminRequiredMixin, View):
    def get(self, request):
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