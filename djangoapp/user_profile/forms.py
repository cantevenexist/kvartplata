from django import forms
from .models import UserProfile
from allauth.socialaccount.forms import SignupForm
from django.conf import settings
from django.contrib.auth.models import User

# user_profile/forms.py
from django import forms
from .models import UserProfile

class UserProfileForm(forms.ModelForm):
    """Форма для редактирования профиля пользователя"""
    
    class Meta:
        model = UserProfile
        fields = [
            'full_name', 'phone_number', 'passport_number', 
            'passport_issued_by', 'passport_issued_date', 
            'registration_address', 'actual_address', 'birth_date'
        ]
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'passport_issued_date': forms.DateInput(attrs={'type': 'date'}),
            'registration_address': forms.Textarea(attrs={'rows': 3}),
            'actual_address': forms.Textarea(attrs={'rows': 3}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Делаем все поля необязательными
        for field in self.fields:
            self.fields[field].required = False

class CustomSignupForm(SignupForm):
    username = forms.CharField(label="Username")

    def __init__(self, *args, **kwargs):
        super(CustomSignupForm, self).__init__(*args, **kwargs)

        if not settings.SOCIALACCOUNT_EMAIL_REQUIRED:
            if 'email' in self.fields:
                self.fields['email'].widget = forms.HiddenInput()

    def clean_username(self):
        username = self.cleaned_data.get('username')

        if User.objects.filter(username=username).exists():
            self.add_error('username', "Этот логин уже занят.")
        if username.lower() in settings.ACCOUNT_USERNAME_BLACKLIST:
            self.add_error('username', "Такое имя пользователя не может быть использовано, выберите другое.")
        if len(username) < settings.ACCOUNT_USERNAME_MIN_LENGTH:
            self.add_error('username', "Увеличьте имя пользователя до 4 символов или более.")

        return username

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data

    def save(self, request):
        user = super().save(request)
        user.username = self.cleaned_data['username']

        if not settings.SOCIALACCOUNT_EMAIL_REQUIRED:
            user.email = ''

        user.save()

        return user