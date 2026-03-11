from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator

class UserProfile(models.Model):
    # Связь с пользователем
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='profile'
    )
    
    full_name = models.CharField(max_length=255, blank=True, null=True,verbose_name='Полное имя')
    phone_number = models.CharField(max_length=20,blank=True,null=True,verbose_name='Номер телефона')
    passport_number = models.CharField(max_length=50,blank=True,null=True,verbose_name='Номер паспорта')
    passport_issued_by = models.CharField(max_length=255,blank=True,null=True,verbose_name='Кем выдан паспорт')
    passport_issued_date = models.DateField(blank=True,null=True,verbose_name='Дата выдачи паспорта')
    registration_address = models.TextField(blank=True, null=True,verbose_name='Адрес регистрации')
    actual_address = models.TextField(blank=True,null=True,verbose_name='Фактический адрес')
    birth_date = models.DateField(blank=True,null=True,verbose_name='Дата рождения')
    
    # Мета-информация
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    
    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'
    
    def __str__(self):
        return self.user.username
    


class Notification(models.Model):
    LEVELS = (
        ('info', 'Информация'),
        ('warning', 'Предупреждение'),
        ('error', 'Ошибка'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    level = models.CharField(max_length=10, choices=LEVELS, default='info')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    related_url = models.URLField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.level.upper()}] {self.message[:50]}"