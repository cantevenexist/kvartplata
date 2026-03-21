from django.urls import path
from . import views

app_name ='buh_panel'

urlpatterns = [
    path('', views.BuhPanelView.as_view(), name='buh_panel'),
]