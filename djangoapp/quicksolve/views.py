from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse

@login_required
def login_redirect(request):
    """
    Перенаправляет пользователя после входа в зависимости от роли
    """
    user = request.user
    
    # Суперпользователь -> админка
    if user.is_superuser:
        return redirect('admin_panel:admin_panel')
    
    # Бухгалтер (staff) -> панель бухгалтера
    elif user.is_staff:
        return redirect('buh_panel:buh_panel')  # или ваша панель бухгалтера
    
    # Обычный пользователь -> профиль
    else:
        return redirect('user_profile:my_profile')  # или 'profile'