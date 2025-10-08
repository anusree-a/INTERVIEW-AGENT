from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('admin-login/', views.admin_login, name='admin_login'),
    path('hr-login/', views.hr_login, name='hr_login'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('hr-dashboard/', views.hr_dashboard, name='hr_dashboard'),
    path('logout/', views.user_logout, name='logout'),
    
    # Company registration and management
    path('company-registration/', views.company_registration, name='company_registration'),
    path('select-plan/', views.select_plan, name='select_plan'),
    path('payment-gateway/', views.payment_gateway, name='payment_gateway'),
    path('company-login/', views.company_login, name='company_login'),
    path('company-admin-dashboard/', views.company_admin_dashboard, name='company_admin_dashboard'),
]