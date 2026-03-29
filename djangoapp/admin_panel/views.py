from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.views import View
from django.contrib import messages
from django.db.models import Q
from housing.forms import HousingUnitForm, OwnerSearchForm
from housing.models import HousingUnit
from user_profile.models import UserProfile
from user_profile.forms import UserProfileForm
from django.http import Http404
from payment_service.models import Tariff
from django.utils import timezone

class AdminRequiredMixin(UserPassesTestMixin):
    """Миксин для проверки прав администратора"""
    def test_func(self):
        return self.request.user.is_superuser
    
    def handle_no_permission(self):
        raise Http404('Нет доступа')

class AdminPanelView(LoginRequiredMixin, AdminRequiredMixin, View):
    """Главная страница панели администратора"""
    
    def get(self, request):
        # Статистика пользователей
        total_users = User.objects.count()
        staff_users = User.objects.filter(is_staff=True).count()
        regular_users = total_users - staff_users
        
        # Статистика жилья
        total_housing = HousingUnit.objects.count()
        
        # Статистика тарифов
        now = timezone.now().date()
        tariffs = Tariff.objects.all()
        
        active_tariffs = tariffs.filter(
            Q(is_active=True) & 
            (Q(valid_to__isnull=True) | Q(valid_to__gte=now))
        ).count()
        
        expired_tariffs = tariffs.filter(
            Q(is_active=True) & 
            Q(valid_to__lt=now)
        ).count()
        
        archived_tariffs = tariffs.filter(is_active=False).count()
        
        context = {
            # Статистика для общей карточки
            'users_count': total_users,
            'housing_count': total_housing,
            'active_tariffs_count': active_tariffs,
            
            # Детальная статистика для карточки тарифов
            'active_tariffs_count_detail': active_tariffs,
            'expired_tariffs_count': expired_tariffs,
            'archived_tariffs_count': archived_tariffs,
            
            # Дополнительная статистика (опционально)
            'staff_users_count': staff_users,
            'regular_users_count': regular_users,
        }
        
        return render(request, 'admin_panel/admin_panel.html', context)
    

class RegisterUserView(LoginRequiredMixin, AdminRequiredMixin, View):
    """Регистрация нового пользователя"""
    
    def get(self, request):
        return render(request, 'admin_panel/register_user.html')
    
    def post(self, request):
        user_type = request.POST.get('user_type')
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        # Проверка паролей
        if password != confirm_password:
            messages.error(request, 'Пароли не совпадают')
            # Сохраняем введенные данные для возврата в форму
            request.session['form_data'] = {
                'user_type': user_type,
                'username': username,
                'email': email,
                'full_name': request.POST.get('full_name'),
                'birth_date': request.POST.get('birth_date'),
                'phone_number': request.POST.get('phone_number'),
                'passport_number': request.POST.get('passport_number'),
                'passport_issued_by': request.POST.get('passport_issued_by'),
                'passport_issued_date': request.POST.get('passport_issued_date'),
                'registration_address': request.POST.get('registration_address'),
                'actual_address': request.POST.get('actual_address'),
            }
            return redirect('admin_panel:register_user')
        
        # Проверка длины пароля
        if len(password) < 8:
            messages.error(request, 'Пароль должен содержать минимум 8 символов')
            request.session['form_data'] = {
                'user_type': user_type,
                'username': username,
                'email': email,
                'full_name': request.POST.get('full_name'),
                'birth_date': request.POST.get('birth_date'),
                'phone_number': request.POST.get('phone_number'),
                'passport_number': request.POST.get('passport_number'),
                'passport_issued_by': request.POST.get('passport_issued_by'),
                'passport_issued_date': request.POST.get('passport_issued_date'),
                'registration_address': request.POST.get('registration_address'),
                'actual_address': request.POST.get('actual_address'),
            }
            return redirect('admin_panel:register_user')
        
        # Проверки на существование пользователя
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Пользователь с таким именем уже существует')
            request.session['form_data'] = {
                'user_type': user_type,
                'username': username,
                'email': email,
                'full_name': request.POST.get('full_name'),
                'birth_date': request.POST.get('birth_date'),
                'phone_number': request.POST.get('phone_number'),
                'passport_number': request.POST.get('passport_number'),
                'passport_issued_by': request.POST.get('passport_issued_by'),
                'passport_issued_date': request.POST.get('passport_issued_date'),
                'registration_address': request.POST.get('registration_address'),
                'actual_address': request.POST.get('actual_address'),
            }
            return redirect('admin_panel:register_user')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Пользователь с таким email уже существует')
            request.session['form_data'] = {
                'user_type': user_type,
                'username': username,
                'email': email,
                'full_name': request.POST.get('full_name'),
                'birth_date': request.POST.get('birth_date'),
                'phone_number': request.POST.get('phone_number'),
                'passport_number': request.POST.get('passport_number'),
                'passport_issued_by': request.POST.get('passport_issued_by'),
                'passport_issued_date': request.POST.get('passport_issued_date'),
                'registration_address': request.POST.get('registration_address'),
                'actual_address': request.POST.get('actual_address'),
            }
            return redirect('admin_panel:register_user')
        
        # Создание пользователя
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_staff=(user_type == 'accountant')  # True для бухгалтера
        )
        
        # Если владелец квартиры - заполняем профиль
        if user_type == 'owner':
            profile = user.profile  # профиль создается сигналом
            profile.full_name = request.POST.get('full_name')
            profile.birth_date = request.POST.get('birth_date') or None
            profile.phone_number = request.POST.get('phone_number')
            profile.passport_number = request.POST.get('passport_number')
            profile.passport_issued_by = request.POST.get('passport_issued_by')
            profile.passport_issued_date = request.POST.get('passport_issued_date') or None
            profile.registration_address = request.POST.get('registration_address')
            profile.actual_address = request.POST.get('actual_address')
            profile.save()
            
            messages.success(request, f'Владелец квартиры {username} успешно создан')
        else:
            messages.success(request, f'Бухгалтер {username} успешно создан')
        
        # Очищаем сохраненные данные из сессии
        if 'form_data' in request.session:
            del request.session['form_data']
        
        return redirect('admin_panel:admin_panel')

class RegisterHousingView(LoginRequiredMixin, AdminRequiredMixin, View):
    """Регистрация нового жилого помещения"""
    template_name = 'admin_panel/register_housing.html'
    
    def get(self, request):
        form = HousingUnitForm()
        search_form = OwnerSearchForm()
        
        context = {
            'form': form,
            'search_form': search_form,
            'search_results': [],
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        action = request.POST.get('action')
        
        # Поиск пользователей
        if action == 'search':
            search_form = OwnerSearchForm(request.POST)
            form = HousingUnitForm()
            
            if search_form.is_valid():
                query = search_form.cleaned_data['search_query']
                
                if query:
                    # Ищем пользователей, которые НЕ являются бухгалтерами (is_staff=False)
                    users = User.objects.filter(
                        Q(is_staff=False),
                        Q(username__icontains=query) |
                        Q(email__icontains=query) |
                        Q(profile__full_name__icontains=query) |
                        Q(profile__phone_number__icontains=query) |
                        Q(profile__passport_number__icontains=query)
                    ).distinct()[:10]
                    
                    search_results = []
                    for user in users:
                        profile = user.profile
                        search_results.append({
                            'id': user.id,
                            'username': user.username,
                            'email': user.email,
                            'full_name': profile.full_name or 'Не указано',
                            'phone': profile.phone_number or 'Не указан',
                            'passport': profile.passport_number or 'Не указан',
                        })
                else:
                    search_results = []
                
                context = {
                    'form': form,
                    'search_form': search_form,
                    'search_results': search_results,
                    'search_performed': bool(query),
                }
                return render(request, self.template_name, context)
        
        # Создание жилого помещения
        elif action == 'create':
            form = HousingUnitForm(request.POST)
            owner_id = request.POST.get('owner_id')
            
            if form.is_valid():
                housing_unit = form.save(commit=False)
                
                if owner_id:
                    try:
                        owner = User.objects.get(id=owner_id, is_staff=False)
                        housing_unit.owner = owner
                    except User.DoesNotExist:
                        messages.error(request, 'Выбранный пользователь не найден или является бухгалтером')
                        return redirect('admin_panel:register_housing')
                
                housing_unit.created_by = request.user
                housing_unit.save()
                
                messages.success(request, f'Жилое помещение по адресу {housing_unit.address} успешно добавлено')
                return redirect('admin_panel:admin_panel')
            else:
                search_form = OwnerSearchForm()
                context = {
                    'form': form,
                    'search_form': search_form,
                    'search_results': [],
                }
                return render(request, self.template_name, context)
        
        return redirect('admin_panel:register_housing')

class SearchUserView(LoginRequiredMixin, AdminRequiredMixin, View):
    """Поиск пользователей для редактирования"""
    template_name = 'admin_panel/search_user.html'
    
    def get(self, request):
        query = ''
        results = []
        users = User.objects.exclude(is_superuser=True)
        
        for user in users:
            profile = user.profile
            results.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': profile.full_name or 'Не указано',
                'phone': profile.phone_number or 'Не указан',
                'passport': profile.passport_number or 'Не указан',
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
            })

        context = {
            'results': results,
            'query': query,
            'total_count': len(results),
            'showing_all': not query,
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        query = request.POST.get('search_query', '')
        user_type = request.POST.get('user_type', 'all')
        
        results = []
        
        # Базовый queryset - все пользователи
        users = User.objects.exclude(is_superuser=True)
        
        # Если есть поисковый запрос, фильтруем по нему
        if query:
            users = users.filter(
                Q(username__icontains=query) |
                Q(email__icontains=query) |
                Q(profile__full_name__icontains=query) |
                Q(profile__phone_number__icontains=query) |
                Q(profile__passport_number__icontains=query)
            )
        
        # Фильтруем по типу пользователя
        if user_type == 'staff':
            users = users.filter(is_staff=True)
        elif user_type == 'owners':
            users = users.filter(is_staff=False, is_superuser=False)
        
        # Ограничиваем количество результатов
        # users = users.distinct()[:50]  # Показываем до 50 пользователей
        
        for user in users:
            profile = user.profile
            results.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': profile.full_name or 'Не указано',
                'phone': profile.phone_number or 'Не указан',
                'passport': profile.passport_number or 'Не указан',
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
            })
        
        context = {
            'results': results,
            'query': query,
            'user_type': user_type,
            'total_count': len(results),
            'showing_all': not query,  # Флаг, показываем ли всех пользователей
        }
        return render(request, self.template_name, context)

class EditProfileView(LoginRequiredMixin, AdminRequiredMixin, View):
    """Редактирование профиля пользователя (только для суперпользователя)"""
    template_name = 'admin_panel/edit_profile.html'
    
    def get(self, request, user_id):
        # Получаем пользователя и его профиль
        user = get_object_or_404(User, id=user_id)
        profile = get_object_or_404(UserProfile, user=user)
        
        if profile.user.is_superuser:
            raise Http404('Нет доступа')

        form = UserProfileForm(instance=profile)
        
        context = {
            'form': form,
            'edit_user': user,
            'profile': profile,
        }
        return render(request, self.template_name, context)
    
    def post(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        profile = get_object_or_404(UserProfile, user=user)
        
        # Проверяем, не является ли это запросом на смену пароля
        if 'change_password' in request.POST:
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            if new_password and confirm_password:
                if new_password == confirm_password:
                    if len(new_password) >= 8:
                        user.set_password(new_password)
                        user.save()
                        messages.success(request, f'Пароль для пользователя {user.username} успешно изменен')
                    else:
                        messages.error(request, 'Пароль должен содержать минимум 8 символов')
                else:
                    messages.error(request, 'Пароли не совпадают')
            else:
                messages.error(request, 'Заполните все поля пароля')
            
            return redirect('admin_panel:edit_profile', user_id=user.id)
        
        # Обычное редактирование профиля
        form = UserProfileForm(request.POST, instance=profile)
        
        if form.is_valid():
            form.save()
            messages.success(request, f'Профиль пользователя {user.username} успешно обновлен')
            return redirect('profile', username=user.username)
        
        context = {
            'form': form,
            'edit_user': user,
            'profile': profile,
        }
        return render(request, self.template_name, context)

class SearchHousingView(LoginRequiredMixin, AdminRequiredMixin, View):
    """Поиск жилых помещений для редактирования"""
    template_name = 'admin_panel/search_housing.html'
    
    def get(self, request):
        query = ''
        results = []
        units = HousingUnit.objects.all()
        
        for unit in units:
            try:
                user = unit.owner
                profile = user.profile
                results.append({
                    'unitid': unit.id,
                    'unit': unit,
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'full_name': profile.full_name or 'Не указано',
                    'phone': profile.phone_number or 'Не указан',
                    'passport': profile.passport_number or 'Не указан',
                })
            except:
                results.append({
                    'unitid': unit.id,
                    'unit': unit,
                })

        context = {
            'results': results,
            'query': query,
            'total_count': len(results),
            'showing_all': not query,
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        query = request.POST.get('search_query', '')        
        results = []
        
        # Базовый queryset - все пользователи
        units = HousingUnit.objects.all()
        
        # Если есть поисковый запрос, фильтруем по нему
        if query:
            units = units.filter(
                Q(address__icontains=query) |
                Q(owner__username__icontains=query) |
                Q(owner__email__icontains=query) |
                Q(owner__profile__full_name__icontains=query) |
                Q(owner__profile__phone_number__icontains=query) |
                Q(owner__profile__passport_number__icontains=query)
            )
        
        
        # Ограничиваем количество результатов
        # users = users.distinct()[:50]  # Показываем до 50 пользователей
        
        for unit in units:
            try:
                user = unit.owner
                profile = user.profile
                results.append({
                    'unitid': unit.id,
                    'unit': unit,
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'full_name': profile.full_name or 'Не указано',
                    'phone': profile.phone_number or 'Не указан',
                    'passport': profile.passport_number or 'Не указан',
                })
            except:
                results.append({
                    'unitid': unit.id,
                    'unit': unit,
                })

        context = {
            'results': results,
            'query': query,
            'total_count': len(results),
            'showing_all': not query,
        }
        return render(request, self.template_name, context)

class EditHousingView(LoginRequiredMixin, AdminRequiredMixin, View):
    """Редактирование жилого помещения (только для администратора)"""
    template_name = 'admin_panel/edit_housing.html'
    
    def get(self, request, unit_id):
        unit = get_object_or_404(HousingUnit, id=unit_id)
        form = HousingUnitForm(instance=unit)
        search_form = OwnerSearchForm()
        
        # Информация о текущем владельце
        current_owner = unit.owner
        
        context = {
            'form': form,
            'search_form': search_form,
            'edit_unit': unit,
            'current_owner': current_owner,
            'search_results': [],
        }
        return render(request, self.template_name, context)
    
    def post(self, request, unit_id):
        unit = get_object_or_404(HousingUnit, id=unit_id)
        action = request.POST.get('action')
        
        # Поиск пользователей
        if action == 'search':
            search_form = OwnerSearchForm(request.POST)
            form = HousingUnitForm(instance=unit)
            
            if search_form.is_valid():
                query = search_form.cleaned_data['search_query']
                
                if query:
                    # Ищем пользователей, которые НЕ являются бухгалтерами (is_staff=False)
                    users = User.objects.filter(
                        Q(is_staff=False),
                        Q(username__icontains=query) |
                        Q(email__icontains=query) |
                        Q(profile__full_name__icontains=query) |
                        Q(profile__phone_number__icontains=query) |
                        Q(profile__passport_number__icontains=query)
                    ).distinct()[:10]
                    
                    search_results = []
                    for user in users:
                        profile = user.profile
                        search_results.append({
                            'id': user.id,
                            'username': user.username,
                            'email': user.email,
                            'full_name': profile.full_name or 'Не указано',
                            'phone': profile.phone_number or 'Не указан',
                            'passport': profile.passport_number or 'Не указан',
                        })
                else:
                    search_results = []
                
                context = {
                    'form': form,
                    'search_form': search_form,
                    'edit_unit': unit,
                    'current_owner': unit.owner,
                    'search_results': search_results,
                    'search_performed': bool(query),
                }
                return render(request, self.template_name, context)
        
        # Сохранение изменений
        elif action == 'save':
            form = HousingUnitForm(request.POST, instance=unit)
            owner_id = request.POST.get('owner_id')
            
            if form.is_valid():
                housing_unit = form.save(commit=False)
                
                # Обновляем владельца, если выбран новый
                if owner_id:
                    try:
                        owner = User.objects.get(id=owner_id, is_staff=False)
                        housing_unit.owner = owner
                        messages.info(request, f'Владелец изменен на {owner.username}')
                    except User.DoesNotExist:
                        messages.error(request, 'Выбранный пользователь не найден или является бухгалтером')
                        return redirect('admin_panel:edit_housing', unit_id=unit.id)
                else:
                    # Если owner_id не указан, можно либо оставить старого, либо убрать
                    # Вариант 1: оставить старого владельца
                    # housing_unit.owner = unit.owner
                    
                    # Вариант 2: убрать владельца (если нужно)
                    if request.POST.get('remove_owner') == 'on':
                        housing_unit.owner = None
                        messages.info(request, 'Владелец удален')
                
                housing_unit.save()
                messages.success(request, f'Данные жилого помещения {housing_unit.address} успешно обновлены')
                return redirect('admin_panel:search_housing')
            
            # Если форма не валидна
            search_form = OwnerSearchForm()
            context = {
                'form': form,
                'search_form': search_form,
                'edit_unit': unit,
                'current_owner': unit.owner,
                'search_results': [],
            }
            return render(request, self.template_name, context)
        
        return redirect('admin_panel:edit_housing', unit_id=unit.id)
