from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views import View
from django.http import Http404

class BuhRequiredMixin(UserPassesTestMixin):
    """Миксин для проверки прав бухгалтера"""
    def test_func(self):
        return self.request.user.is_staff and not self.request.user.is_superuser
    
    def handle_no_permission(self):
        raise Http404('Нет доступа')

class BuhPanelView(LoginRequiredMixin, BuhRequiredMixin, View):
    """Главная страница панели бухгалтера"""
    
    def get(self, request):
        return render(request, 'buh_panel/buh_panel.html')
