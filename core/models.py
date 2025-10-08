from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator

class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    duration_months = models.PositiveIntegerField(default=1)
    max_hr_accounts = models.PositiveIntegerField(default=5)
    max_interviews_per_month = models.PositiveIntegerField(default=100)
    features = models.JSONField(default=list, help_text="List of features included in this plan")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Subscription Plan'
        verbose_name_plural = 'Subscription Plans'

class Company(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ]
    
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    contact_person = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    address = models.TextField()
    industry = models.CharField(max_length=100)
    company_size = models.CharField(max_length=50)
    website = models.URLField(blank=True, null=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    subscription_plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    subscription_start_date = models.DateTimeField(null=True, blank=True)
    subscription_end_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Company'
        verbose_name_plural = 'Companies'

class HRProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='added_hrs')
    added_on = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'HR Profile'
        verbose_name_plural = 'HR Profiles'