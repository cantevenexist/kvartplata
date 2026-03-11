from django.urls import path
from . import views

app_name = 'housing'

urlpatterns = [
    # Мои квартиры (редирект на список квартир текущего пользователя)
    path('my/', views.MyHousingView.as_view(), name='my_housing'),
    
    # Список квартир пользователя
    path('<str:username>/', views.UserHousingListView.as_view(), name='user_housing_list'),
    
    # Конкретная квартира
    path('unit/<int:unit_id>/', views.HousingDetailView.as_view(), name='housing_detail'),
]