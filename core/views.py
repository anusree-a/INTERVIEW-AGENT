from django.shortcuts import render

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User
from .models import HRProfile
from .forms import AdminLoginForm, HRLoginForm, AddHRForm

def home(request):
    return render(request, 'core/home.html')

def admin_login(request):
    if request.method == 'POST':
        form = AdminLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            
            if user is not None and user.is_superuser:
                login(request, user)
                return redirect('admin_dashboard')
            else:
                messages.error(request, 'Invalid admin credentials')
    else:
        form = AdminLoginForm()
    
    return render(request, 'core/admin_login.html', {'form': form})

def hr_login(request):
    if request.method == 'POST':
        form = HRLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            
            try:
                hr_profile = HRProfile.objects.get(email=email)
                user = authenticate(request, username=hr_profile.user.username, password=password)
                
                if user is not None:
                    login(request, user)
                    return redirect('hr_dashboard')
                else:
                    messages.error(request, 'Invalid credentials')
            except HRProfile.DoesNotExist:
                messages.error(request, 'HR not found')
    else:
        form = HRLoginForm()
    
    return render(request, 'core/hr_login.html', {'form': form})

def is_admin(user):
    return user.is_superuser

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    hrs = HRProfile.objects.all()
    
    if request.method == 'POST':
        form = AddHRForm(request.POST)
        if form.is_valid():
            # Create user
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            
            username = email.split('@')[0]
            
            if User.objects.filter(username=username).exists():
                messages.error(request, 'User already exists')
            else:
                user = User.objects.create_user(username=username, email=email, password=password)
                
                # Create HR profile
                hr_profile = form.save(commit=False)
                hr_profile.user = user
                hr_profile.added_by = request.user
                hr_profile.save()
                
                messages.success(request, f'HR {name} added successfully')
                return redirect('admin_dashboard')
    else:
        form = AddHRForm()
    
    context = {
        'form': form,
        'hrs': hrs
    }
    return render(request, 'core/admin_dashboard.html', context)

@login_required
def hr_dashboard(request):
    try:
        hr_profile = HRProfile.objects.get(user=request.user)
        context = {
            'hr': hr_profile
        }
        return render(request, 'core/hr_dashboard.html', context)
    except HRProfile.DoesNotExist:
        messages.error(request, 'HR profile not found')
        return redirect('home')

def user_logout(request):
    logout(request)
    return redirect('home')
