from django.shortcuts import render

from django.shortcuts import render, get_object_or_404
from .models import InterviewSession

def interview_page(request, token):
    session = get_object_or_404(InterviewSession, token=token)
    return render(request, "interview.html", {"session": session})

