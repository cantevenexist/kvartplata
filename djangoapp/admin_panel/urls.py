from django.urls import path
from . import views

app_name ='admin_panel'

urlpatterns = [
    path('', views.AdminPanelView.as_view(), name='admin_panel'),
    path('register_user/', views.RegisterUserView.as_view(), name='register_user'),
    path('register_housing/', views.RegisterHousingView.as_view(), name='register_housing'),
    path('search_user/', views.SearchUserView.as_view(), name='search_user'),
    path('edit_profile/<int:user_id>/', views.EditProfileView.as_view(), name='edit_profile'),
    path('search_housing/', views.SearchHousingView.as_view(), name='search_housing'),
    path('edit_housing/<int:unit_id>/', views.EditHousingView.as_view(), name='edit_housing'),
]