from django.urls import path
from .views import interview_page

urlpatterns = [
    path("interview/<uuid:token>/", interview_page),
]
