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
]