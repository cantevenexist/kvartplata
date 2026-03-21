# housing/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

class HousingUnit(models.Model):
    """Модель жилого помещения"""
    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_housing_units',
        verbose_name='Владелец'
    )
    address = models.CharField(
        max_length=255,
        verbose_name='Адрес'
    )
    prepayment = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Аванс (переплата)'
    )
    total_area = models.FloatField(
        verbose_name='Общая площадь (м²)'
    )
    
    # Метаданные
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    
    class Meta:
        verbose_name = 'Жилое помещение'
        verbose_name_plural = 'Жилые помещения'
        ordering = ['address']
    
    def __str__(self):
        return self.address