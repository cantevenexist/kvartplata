from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from .models import User, UserProfile, Notification
from django.http import JsonResponse
import uuid
from django.http import Http404

class MyProfileView(LoginRequiredMixin, View):
    def get(self, request):
        return redirect('profile', username=request.user.username)


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