from django.contrib import admin

# Register your models here.

from django.contrib import admin
from .models import HRProfile

@admin.register(HRProfile)
class HRProfileAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'added_by', 'added_on', 'is_active']
    list_filter = ['is_active', 'added_on']
    search_fields = ['name', 'email']