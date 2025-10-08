#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to Python path
sys.path.append('/Users/alokhk/Desktop/INTERVIEW-AGENT-main')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
django.setup()

from core.models import SubscriptionPlan

# Create sample subscription plans
plans_data = [
    {
        'name': 'Basic Plan',
        'description': 'Perfect for small companies getting started with interview management.',
        'price': 29.99,
        'duration_months': 1,
        'max_hr_accounts': 2,
        'max_interviews_per_month': 25,
        'features': [
            'Basic interview scheduling',
            'Candidate management',
            'Email notifications',
            'Basic reporting'
        ]
    },
    {
        'name': 'Professional Plan',
        'description': 'Ideal for growing companies with multiple HR team members.',
        'price': 79.99,
        'duration_months': 1,
        'max_hr_accounts': 5,
        'max_interviews_per_month': 100,
        'features': [
            'Advanced interview scheduling',
            'Candidate management',
            'HR team collaboration',
            'Advanced reporting & analytics',
            'Custom interview workflows',
            'Integration with job boards',
            'Priority support'
        ]
    },
    {
        'name': 'Enterprise Plan',
        'description': 'For large organizations with extensive hiring needs.',
        'price': 199.99,
        'duration_months': 1,
        'max_hr_accounts': 20,
        'max_interviews_per_month': 500,
        'features': [
            'Unlimited interview scheduling',
            'Advanced candidate management',
            'Multi-team collaboration',
            'Comprehensive reporting & analytics',
            'Custom interview workflows',
            'API access',
            'Integration with HR systems',
            'White-label options',
            '24/7 dedicated support'
        ]
    }
]

# Create plans
for plan_data in plans_data:
    plan, created = SubscriptionPlan.objects.get_or_create(
        name=plan_data['name'],
        defaults=plan_data
    )
    if created:
        print(f"Created plan: {plan.name}")
    else:
        print(f"Plan already exists: {plan.name}")

print("Sample subscription plans created successfully!")
