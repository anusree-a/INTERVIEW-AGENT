from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from .models import HRProfile, Company, SubscriptionPlan
from .forms import AdminLoginForm, HRLoginForm, AddHRForm, CompanyRegistrationForm, PlanSelectionForm

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

@login_required(login_url='admin_login')
@user_passes_test(is_admin, login_url='admin_login')
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

@login_required(login_url='hr_login')
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

def company_registration(request):
    if request.method == 'POST':
        form = CompanyRegistrationForm(request.POST)
        if form.is_valid():
            # Create user account
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            username = email.split('@')[0]
            
            # Ensure unique username
            original_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{original_username}_{counter}"
                counter += 1
            
            user = User.objects.create_user(username=username, email=email, password=password)
            
            # Create company profile
            company = form.save(commit=False)
            company.user = user
            company.save()
            
            # Store company ID in session for plan selection
            request.session['company_id'] = company.id
            
            messages.success(request, 'Company registered successfully! Please select a subscription plan.')
            return redirect('select_plan')
    else:
        form = CompanyRegistrationForm()
    
    return render(request, 'core/company_registration.html', {'form': form})

def select_plan(request):
    # Check if company is in session
    company_id = request.session.get('company_id')
    if not company_id:
        messages.error(request, 'Please complete company registration first.')
        return redirect('company_registration')
    
    company = get_object_or_404(Company, id=company_id)
    plans = SubscriptionPlan.objects.filter(is_active=True)
    
    if request.method == 'POST':
        form = PlanSelectionForm(request.POST)
        if form.is_valid():
            selected_plan = form.cleaned_data['plan']
            company.subscription_plan = selected_plan
            company.save()
            
            # Store plan details in session for payment
            request.session['selected_plan_id'] = selected_plan.id
            
            messages.success(request, f'Plan "{selected_plan.name}" selected. Proceed to payment.')
            return redirect('payment_gateway')
    else:
        form = PlanSelectionForm()
    
    context = {
        'form': form,
        'plans': plans,
        'company': company
    }
    return render(request, 'core/select_plan.html', context)

def payment_gateway(request):
    # Check if company and plan are in session
    company_id = request.session.get('company_id')
    plan_id = request.session.get('selected_plan_id')
    
    if not company_id or not plan_id:
        messages.error(request, 'Please complete registration and plan selection first.')
        return redirect('company_registration')
    
    company = get_object_or_404(Company, id=company_id)
    plan = get_object_or_404(SubscriptionPlan, id=plan_id)
    
    if request.method == 'POST':
        # Simulate payment processing
        payment_method = request.POST.get('payment_method')
        
        if payment_method:
            # Update company status and subscription dates
            company.status = 'active'
            company.subscription_start_date = timezone.now()
            company.subscription_end_date = timezone.now() + timedelta(days=plan.duration_months * 30)
            company.save()
            
            # Clear session data
            request.session.pop('company_id', None)
            request.session.pop('selected_plan_id', None)
            
            # Log in the company user explicitly after successful payment
            user = company.user
            # Set the authentication backend so Django can log the user in
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            
            messages.success(request, f'Payment successful! Welcome to {plan.name}. You can now access your admin panel.')
            return redirect('company_admin_dashboard')
        else:
            messages.error(request, 'Please select a payment method.')
    
    context = {
        'company': company,
        'plan': plan
    }
    return render(request, 'core/payment_gateway.html', context)

@login_required(login_url='company_login')
def company_admin_dashboard(request):
    try:
        company = Company.objects.get(user=request.user)
        
        # Check if subscription is active
        if company.status != 'active':
            messages.warning(request, 'Your subscription is not active. Please contact support.')
        
        # Get HR profiles for this company
        hr_profiles = HRProfile.objects.filter(company=company)
        
        context = {
            'company': company,
            'hr_profiles': hr_profiles
        }
        return render(request, 'core/company_admin_dashboard.html', context)
    except Company.DoesNotExist:
        messages.error(request, 'Company profile not found.')
        return redirect('home')

def company_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        try:
            company = Company.objects.get(email=email)
            user = authenticate(request, username=company.user.username, password=password)
            
            if user is not None:
                if company.status == 'active':
                    login(request, user)
                    return redirect('company_admin_dashboard')
                else:
                    messages.error(request, 'Your subscription is not active. Please contact support.')
            else:
                messages.error(request, 'Invalid credentials')
        except Company.DoesNotExist:
            messages.error(request, 'Company not found')
    else:
        email = request.GET.get('email', '')
    
    return render(request, 'core/company_login.html', {'email': email})
