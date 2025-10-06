from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('admin-login/', views.admin_login, name='admin_login'),
    path('hr-login/', views.hr_login, name='hr_login'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('hr-dashboard/', views.hr_dashboard, name='hr_dashboard'),
    path('logout/', views.user_logout, name='logout'),
]