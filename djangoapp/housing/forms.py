from django import forms
from django.contrib.auth.models import User
from user_profile.models import UserProfile
from .models import HousingUnit

class HousingUnitForm(forms.ModelForm):
    """Форма для создания жилого помещения"""
    
    class Meta:
        model = HousingUnit
        fields = ['address', 'total_area']
        widgets = {
            'address': forms.TextInput(attrs={
                'placeholder': 'Введите адрес',
                'style': 'width: 300px;'
            }),
            'total_area': forms.NumberInput(attrs={
                'placeholder': 'Площадь в м²',
                'step': '0.1',
                'style': 'width: 100px;'
            }),
        }

class OwnerSearchForm(forms.Form):
    """Форма поиска владельца"""
    search_query = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Поиск по имени, телефону или паспорту...',
            'style': 'width: 300px;'
        })
    )