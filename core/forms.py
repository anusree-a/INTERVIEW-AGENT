from django import forms
from django.contrib.auth.models import User
from .models import HRProfile, Company, SubscriptionPlan

class AdminLoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )

class HRLoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )

class AddHRForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )
    
    class Meta:
        model = HRProfile
        fields = ['name', 'email']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'HR Name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'HR Email'
            })
        }

class CompanyRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Create a strong password'
        }),
        help_text="Password must be at least 8 characters long"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your password'
        })
    )
    
    class Meta:
        model = Company
        fields = ['name', 'email', 'contact_person', 'phone', 'address', 'industry', 'company_size', 'website']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Company Name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Company Email'
            }),
            'contact_person': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Contact Person Name'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone Number'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Company Address',
                'rows': 3
            }),
            'industry': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Industry (e.g., Technology, Finance)'
            }),
            'company_size': forms.Select(attrs={
                'class': 'form-control'
            }, choices=[
                ('1-10', '1-10 employees'),
                ('11-50', '11-50 employees'),
                ('51-200', '51-200 employees'),
                ('201-500', '201-500 employees'),
                ('500+', '500+ employees'),
            ]),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'Company Website (optional)'
            })
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password:
            if password != confirm_password:
                raise forms.ValidationError("Passwords don't match")
        
        return cleaned_data

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and Company.objects.filter(email=email).exists():
            raise forms.ValidationError("A company with this email already exists")
        return email

class PlanSelectionForm(forms.Form):
    plan = forms.ModelChoiceField(
        queryset=SubscriptionPlan.objects.filter(is_active=True),
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        empty_label=None
    )
