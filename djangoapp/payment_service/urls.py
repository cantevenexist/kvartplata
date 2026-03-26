# payment_service/urls.py
from django.urls import path
from . import views

app_name = 'payment_service'

urlpatterns = [
    path('tariffs/', views.TariffListView.as_view(), name='tariff_list'),
    path('tariffs/create/', views.TariffCreateView.as_view(), name='tariff_create'),
    path('tariffs/<int:tariff_id>/edit/', views.TariffUpdateView.as_view(), name='tariff_edit'),
    path('tariffs/<int:tariff_id>/archive/', views.TariffArchiveView.as_view(), name='tariff_archive'),
    path('tariffs/<int:tariff_id>/restore/', views.TariffRestoreView.as_view(), name='tariff_restore'),
    path('charges/create/', views.ChargeCreateView.as_view(), name='charge_create'),
    path('charges/', views.ChargeListView.as_view(), name='charge_list'),
    path('payments/create/', views.PaymentCreateView.as_view(), name='payment_create'),
    path('payments/', views.PaymentListView.as_view(), name='payment_list'),
    path('api/register-payment/', views.api_register_payment, name='api_register_payment'),
    path('debts/', views.DebtListView.as_view(), name='debt_list'),
]