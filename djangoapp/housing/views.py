# housing/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.contrib.auth.models import User
from django.http import Http404
from .models import HousingUnit

class MyHousingView(LoginRequiredMixin, View):
    """Редирект на список квартир текущего пользователя"""
    def get(self, request):
        return redirect('housing:user_housing_list', username=request.user.username)

class UserHousingListView(View):
    """Список всех квартир пользователя"""
    template_name = 'housing/user_housing_list.html'
    
    def get(self, request, username):
        user = get_object_or_404(User, username=username)
        
        # Проверка доступа
        is_owner = request.user.is_authenticated and request.user == user
        is_staff = request.user.is_staff
        
        if not is_owner and not is_staff:
            raise Http404("Нет доступа")
        if user.is_staff and not user.is_superuser:
            raise Http404("У бухгалтеров не может быть квартир")
        
        # Получаем квартиры пользователя
        housing_units = HousingUnit.objects.filter(owner=user)
        
        context = {
            'profile_user': user,
            'housing_units': housing_units,
            'is_owner': is_owner,
            'is_staff': is_staff,
            'count': housing_units.count(),
        }
        return render(request, self.template_name, context)

class HousingDetailView(View):
    """Детальная страница квартиры"""
    template_name = 'housing/housing_detail.html'
    
    def get(self, request, unit_id):
        unit = get_object_or_404(HousingUnit, id=unit_id)
        
        # Проверка доступа
        is_owner = request.user.is_authenticated and request.user == unit.owner
        is_staff = request.user.is_staff
        
        if not is_owner and not is_staff:
            raise Http404("Нет доступа")
        
        context = {
            'unit': unit,
            'is_owner': is_owner,
            'is_staff': is_staff,
        }
        return render(request, self.template_name, context)