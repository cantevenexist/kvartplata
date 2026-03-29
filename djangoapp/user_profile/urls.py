from django.urls import path
from . import views

app_name ='user_profile'

urlpatterns = [
    path('my_profile/', views.MyProfileView.as_view(), name='my_profile'),
    path('profile/<str:username>/', views.ProfileView.as_view(), name='profile'),
    path('notifications/<int:notification_id>/', views.NotificationDetailView.as_view(), name='notification_detail'),
    path('notifications/all/', views.AllNotificationsView.as_view(), name='all_notifications'),
    path('notifications/<int:notification_id>/mark-read/', views.MarkNotificationReadView.as_view(), name='mark_notification_read'),
    path('charges/', views.UserChargesView.as_view(), name='user_charges'),
    path('payments/', views.UserPaymentsView.as_view(), name='user_payments'),
    path('debts/', views.UserDebtView.as_view(), name='user_debt'),
]