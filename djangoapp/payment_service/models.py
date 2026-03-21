from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class Tariff(models.Model):
    """
    Модель тарифов для расчета платежей
    """
    UNIT_CHOICES = [
        ('kwh', 'кВт·ч'),
        ('m3', 'м³'),
        ('gcal', 'Гкал'),
        ('m2', 'м²'),
    ]
    
    name = models.CharField(
        max_length=200,
        verbose_name='Название тарифа'
    )
    rate_per_unit = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        validators=[MinValueValidator(0)],
        verbose_name='Ставка за единицу'
    )
    unit = models.CharField(
        max_length=20,
        choices=UNIT_CHOICES,
        verbose_name='Единица измерения'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен'
    )
    valid_to = models.DateField(
        null=True,
        blank=True,
        verbose_name='Действителен до'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Тариф'
        verbose_name_plural = 'Тарифы'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['valid_to']),
        ]

    def __str__(self):
        return f"{self.name} - {self.rate_per_unit} {self.get_unit_display()}"

    def is_valid(self):
        """Проверяет, действителен ли тариф на текущую дату"""
        if not self.is_active:
            return False
        if self.valid_to and self.valid_to < timezone.now().date():
            return False
        return True


class Charge(models.Model):
    """
    Модель начислений за услуги
    """
    housing_id = models.IntegerField(
        db_index=True,
        verbose_name='ID жилья'
    )
    tariff = models.ForeignKey(
        Tariff,
        on_delete=models.PROTECT,
        related_name='charges',
        verbose_name='Тариф'
    )
    period = models.DateField(
        verbose_name='Расчетный период'
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Сумма начисления'
    )
    # Новые поля
    original_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Первоначальная сумма'
    )
    paid_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Оплаченная сумма'
    )
    is_paid = models.BooleanField(
        default=False,
        verbose_name='Полностью оплачено'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Начисление'
        verbose_name_plural = 'Начисления'
        ordering = ['-period', '-created_at']
        unique_together = ['housing_id', 'tariff', 'period']
        indexes = [
            models.Index(fields=['housing_id', 'period']),
            models.Index(fields=['is_paid']),
        ]

    def __str__(self):
        status = "Оплачено" if self.is_paid else f"Осталось {self.remaining_amount}"
        return f"Жилье {self.housing_id} - {self.period} - {self.amount} ({status})"

    @property
    def remaining_amount(self):
        """Оставшаяся сумма к оплате"""
        return self.amount - self.paid_amount

    def add_payment(self, payment_amount):
        """
        Добавить оплату к начислению
        Возвращает остаток платежа, который не был использован
        """
        remaining = self.remaining_amount
        
        if payment_amount >= remaining:
            # Полная оплата
            self.paid_amount += remaining
            self.is_paid = True
            self.save()
            return payment_amount - remaining
        else:
            # Частичная оплата
            self.paid_amount += payment_amount
            self.save()
            return 0

    def save(self, *args, **kwargs):
        # При создании устанавливаем original_amount равным amount
        if not self.pk:
            self.original_amount = self.amount
        super().save(*args, **kwargs)

class Payment(models.Model):
    """
    Модель платежей
    """
    PAYMENT_METHODS = [
        ('cash', 'Наличные'),
        ('card', 'Банковская карта'),
        ('transfer', 'Банковский перевод'),
        ('online', 'Онлайн-платеж'),
        ('automatic', 'Автоматический платеж'),
    ]
    
    housing_id = models.IntegerField(
        db_index=True,
        verbose_name='ID жилья'
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Сумма платежа'
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        verbose_name='Способ оплаты'
    )
    payment_date = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        verbose_name='Дата платежа'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Платеж'
        verbose_name_plural = 'Платежи'
        ordering = ['-payment_date', '-created_at']
        indexes = [
            models.Index(fields=['housing_id', 'payment_date']),
        ]

    def __str__(self):
        return f"Платеж {self.housing_id} - {self.payment_date.date()} - {self.amount}"


class Debt(models.Model):
    """
    Модель задолженностей
    """
    housing_id = models.IntegerField(
        db_index=True,
        verbose_name='ID жилья'
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Общая сумма долга'
    )
    period = models.DateField(
        verbose_name='Период расчета'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Задолженность'
        verbose_name_plural = 'Задолженности'
        ordering = ['-period', '-updated_at']
        unique_together = ['housing_id', 'period']
        indexes = [
            models.Index(fields=['housing_id', 'total_amount']),
        ]

    def __str__(self):
        return f"Долг {self.housing_id} - {self.period} - {self.total_amount}"