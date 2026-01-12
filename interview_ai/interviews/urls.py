from django.urls import path
from . import views

urlpatterns = [
    # Candidate-facing interview pages
    path('interview/<uuid:token>/', views.interview_page, name='interview_page'),
    
    # API endpoints for interview interaction
    path('api/interview/<uuid:token>/start/', views.start_interview_api, name='start_interview'),
    path('api/interview/<uuid:token>/message/', views.send_message_api, name='send_message'),
    path('api/interview/<uuid:token>/cheating/', views.log_cheating_event_api, name='log_cheating'),
    path('api/interview/<uuid:token>/transcribe/', views.transcribe_audio_api, name='transcribe_audio'),
    path('api/interview/<uuid:token>/status/', views.interview_status_api, name='interview_status'),
    
    # HR Dashboard
    path('hr/', views.hr_dashboard, name='hr_dashboard'),
    path('hr/interview/<uuid:token>/', views.interview_detail, name='interview_detail'),
    path('hr/create/', views.create_interview_session, name='create_interview'),
]