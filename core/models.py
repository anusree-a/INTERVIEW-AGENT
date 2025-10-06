from django.db import models

from django.contrib.auth.models import User

class HRProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='added_hrs')
    added_on = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'HR Profile'
        verbose_name_plural = 'HR Profiles'