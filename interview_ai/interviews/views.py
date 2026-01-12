from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.core.files.storage import default_storage
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import json

from .models import InterviewSession, CheatingEvent, Question
from .agent import InterviewAgent
from .resume_parser import parse_resume_for_session


# ============== Interview Page Views ==============

def interview_page(request, token):
    """Main interview interface for candidates"""
    session = get_object_or_404(InterviewSession, token=token)
    
    # Check if interview is still accessible
    if session.status == 'COMPLETED':
        return render(request, 'interview_completed.html', {'session': session})
    
    if session.status == 'TERMINATED':
        return render(request, 'interview_terminated.html', {'session': session})
    
    # Check if resume is required and not uploaded
    require_resume = settings.INTERVIEW_CONFIG.get('REQUIRE_RESUME_UPLOAD', True)
    if require_resume and not session.resume:
        return render(request, 'interview_upload_resume.html', {'session': session})
    
    return render(request, 'interview.html', {'session': session})


# ============== API Endpoints ==============

@api_view(['POST'])
def upload_resume_api(request, token):
    """
    API endpoint for candidate to upload resume before interview
    """
    session = get_object_or_404(InterviewSession, token=token)
    
    if session.status != 'CREATED':
        return Response({
            'error': 'Resume can only be uploaded before interview starts'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    resume_file = request.FILES.get('resume')
    
    if not resume_file:
        return Response({
            'error': 'No resume file provided'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Validate file type
    allowed_extensions = ['.pdf', '.docx']
    file_ext = resume_file.name.lower()[resume_file.name.rfind('.'):]
    
    if file_ext not in allowed_extensions:
        return Response({
            'error': 'Only PDF and DOCX files are allowed'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Validate file size (5MB max)
    if resume_file.size > 5 * 1024 * 1024:
        return Response({
            'error': 'File size must be less than 5MB'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Save resume
    session.resume = resume_file
    session.save()
    
    # Parse resume in background (non-blocking)
    try:
        parse_resume_for_session(session)
    except Exception as e:
        print(f"Resume parsing error: {e}")
        # Continue even if parsing fails
    
    return Response({
        'success': True,
        'message': 'Resume uploaded successfully'
    })


@api_view(['POST'])
def start_interview_api(request, token):
    """
    API endpoint to start the interview
    Called after camera/mic permissions are granted
    """
    session = get_object_or_404(InterviewSession, token=token)
    
    # Check if resume is required
    require_resume = settings.INTERVIEW_CONFIG.get('REQUIRE_RESUME_UPLOAD', True)
    if require_resume and not session.resume:
        return Response({
            'error': 'Please upload your resume first'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Mark permissions as granted
    session.camera_permission = request.data.get('camera_permission', False)
    session.microphone_permission = request.data.get('microphone_permission', False)
    session.save()
    
    # Parse resume if not already done
    if session.resume and not session.parsed_resume_data:
        try:
            parse_resume_for_session(session)
        except Exception as e:
            print(f"Resume parsing error during start: {e}")
    
    # Initialize agent and start interview
    agent = InterviewAgent(session)
    response = agent.start_interview()
    
    return Response({
        'success': True,
        'message': response.get('message'),
        'stage': response.get('stage'),
        'session_status': session.status
    })


@api_view(['POST'])
def send_message_api(request, token):
    """
    API endpoint to send candidate message to AI agent
    Handles both text and transcribed speech
    """
    session = get_object_or_404(InterviewSession, token=token)
    
    if session.status not in ['IN_PROGRESS']:
        return Response({
            'error': 'Interview is not active'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    candidate_message = request.data.get('message', '').strip()
    
    if not candidate_message:
        return Response({
            'error': 'Message cannot be empty'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Process through agent
    agent = InterviewAgent(session)
    response = agent.process_message(candidate_message)
    
    # Check if interview should conclude
    if response.get('action') == 'conclude':
        # Generate final evaluation
        evaluation = agent.generate_final_evaluation()
        
        # Send email to HR
        send_interview_report_email(session)
        
        return Response({
            'success': True,
            'message': response.get('message'),
            'stage': response.get('stage'),
            'action': 'conclude',
            'evaluation': evaluation,
            'session_status': session.status
        })
    
    return Response({
        'success': True,
        'message': response.get('message'),
        'stage': response.get('stage'),
        'action': response.get('action'),
        'session_status': session.status
    })


@api_view(['POST'])
def log_cheating_event_api(request, token):
    """
    API endpoint to log anti-cheating events from frontend
    """
    session = get_object_or_404(InterviewSession, token=token)
    
    event_type = request.data.get('event_type')
    metadata = request.data.get('metadata', {})
    
    if not event_type:
        return Response({
            'error': 'event_type is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Create cheating event
    CheatingEvent.objects.create(
        session=session,
        event_type=event_type,
        metadata=metadata
    )
    
    # Update session cheating score
    session.cheating_score += 1
    session.cheating_events.append({
        'type': event_type,
        'timestamp': timezone.now().isoformat(),
        'metadata': metadata
    })
    session.save()
    
    # Check if threshold exceeded
    threshold = settings.INTERVIEW_CONFIG.get('ANTI_CHEAT_THRESHOLD', 5)
    if session.cheating_score >= threshold:
        # Terminate interview
        session.terminate_interview()
        return Response({
            'success': True,
            'warning': 'Too many violations detected',
            'terminated': True
        })
    
    return Response({
        'success': True,
        'cheating_score': session.cheating_score
    })


@api_view(['POST'])
def transcribe_audio_api(request, token):
    """
    API endpoint for speech-to-text transcription (using Web Speech API)
    Frontend handles transcription, this just receives the text
    """
    session = get_object_or_404(InterviewSession, token=token)
    
    # Frontend sends already transcribed text
    transcription = request.data.get('transcription', '')
    
    if not transcription:
        return Response({
            'error': 'No transcription provided'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    return Response({
        'success': True,
        'transcription': transcription
    })


@api_view(['GET'])
def interview_status_api(request, token):
    """Get current interview status and conversation history"""
    session = get_object_or_404(InterviewSession, token=token)
    
    return Response({
        'status': session.status,
        'stage': session.current_stage,
        'cheating_score': session.cheating_score,
        'questions_asked': session.agent_state.get('questions_asked', 0),
        'conversation_history': session.conversation_history[-10:],
        'resume_uploaded': bool(session.resume)
    })


# ============== HR Dashboard Views ==============

def hr_dashboard(request):
    """Main HR dashboard showing all interviews"""
    from django.db.models import Avg
    sessions = InterviewSession.objects.all().order_by('-created_at')
    
    # Statistics
    total_interviews = sessions.count()
    completed = sessions.filter(status='COMPLETED').count()
    in_progress = sessions.filter(status='IN_PROGRESS').count()
    avg_score = sessions.filter(score__isnull=False).aggregate(
        avg=Avg('score')
    )['avg'] or 0
    
    context = {
        'sessions': sessions,
        'stats': {
            'total': total_interviews,
            'completed': completed,
            'in_progress': in_progress,
            'avg_score': round(avg_score, 2)
        }
    }
    
    return render(request, 'hr_dashboard.html', context)


def interview_detail(request, token):
    """Detailed view of a specific interview for HR"""
    session = get_object_or_404(InterviewSession, token=token)
    questions = Question.objects.filter(session=session)
    cheating_events = CheatingEvent.objects.filter(session=session)
    
    context = {
        'session': session,
        'questions': questions,
        'cheating_events': cheating_events,
    }
    
    return render(request, 'interview_detail.html', context)


def create_interview_session(request):
    """Form to create new interview session (HR doesn't upload resume)"""
    if request.method == 'POST':
        candidate_name = request.POST.get('candidate_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone', '')
        
        # Create session WITHOUT resume (candidate will upload)
        session = InterviewSession.objects.create(
            candidate_name=candidate_name,
            email=email,
            phone=phone
        )
        
        # Send interview link to candidate
        send_interview_invitation_email(session)
        
        return redirect('hr_dashboard')
    
    return render(request, 'create_interview.html')


# ============== Email Utilities ==============

def send_interview_invitation_email(session):
    """Send interview link to candidate"""
    interview_url = f"http://localhost:8000/interview/{session.token}/"
    
    subject = "Your Interview Invitation - AI Interview System"
    message = f"""
Dear {session.candidate_name},

You have been invited to participate in an AI-powered interview session.

Please click the link below to start your interview:
{interview_url}

Important Instructions:
- You will be asked to upload your resume (PDF or DOCX format)
- Ensure you have a stable internet connection
- Allow camera and microphone permissions when prompted
- Find a quiet, well-lit environment
- The interview typically takes 30-45 minutes

Best of luck!

AI Interview System
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [session.email],
        fail_silently=False,
    )


def send_interview_report_email(session):
    """Send interview report to HR after completion"""
    
    subject = f"Interview Report - {session.candidate_name}"
    message = f"""
Interview completed for: {session.candidate_name}
Email: {session.email}
Status: {session.status}

Overall Score: {session.score}/10
Technical Score: {session.technical_score}/10
Communication Score: {session.communication_score}/10

Cheating Violations: {session.cheating_score}

View full report: http://localhost:8000/hr/interview/{session.token}/

{session.evaluation_report}
    """
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [settings.HR_EMAIL],
        fail_silently=False,
    )