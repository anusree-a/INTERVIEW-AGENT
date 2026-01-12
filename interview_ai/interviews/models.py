from django.db import models
import uuid
from django.utils import timezone

class InterviewSession(models.Model):
    STATUS_CHOICES = [
        ('CREATED', 'Created'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('TERMINATED', 'Terminated'),
    ]
    
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    candidate_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    resume = models.FileField(upload_to="resumes/", null=True, blank=True)
    
    # Interview State
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="CREATED")
    current_stage = models.CharField(max_length=50, default="greeting")  # greeting, personal, resume, technical, closing
    
    # AI Agent Memory
    conversation_history = models.JSONField(default=list, blank=True)  # Full chat history
    agent_state = models.JSONField(default=dict, blank=True)  # Agent's internal state
    
    # Resume Analysis
    parsed_resume_data = models.JSONField(default=dict, blank=True)  # Extracted skills, experience
    
    # Responses & Transcript
    transcript = models.TextField(blank=True)
    responses = models.JSONField(default=list, blank=True)  # Structured Q&A pairs
    
    # Anti-cheating
    cheating_events = models.JSONField(default=list, blank=True)
    cheating_score = models.IntegerField(default=0)  # Total violations count
    
    # Evaluation
    score = models.FloatField(null=True, blank=True)
    technical_score = models.FloatField(null=True, blank=True)
    communication_score = models.FloatField(null=True, blank=True)
    evaluation_report = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Permissions granted
    camera_permission = models.BooleanField(default=False)
    microphone_permission = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.candidate_name} - {self.status}"
    
    def start_interview(self):
        self.status = 'IN_PROGRESS'
        self.started_at = timezone.now()
        self.save()
    
    def complete_interview(self):
        self.status = 'COMPLETED'
        self.completed_at = timezone.now()
        self.save()
    
    def terminate_interview(self):
        self.status = 'TERMINATED'
        self.completed_at = timezone.now()
        self.save()


class CheatingEvent(models.Model):
    EVENT_TYPES = [
        ('TAB_SWITCH', 'Tab Switch'),
        ('WINDOW_BLUR', 'Window Lost Focus'),
        ('VISIBILITY_HIDDEN', 'Page Hidden'),
        ('CAMERA_OFF', 'Camera Turned Off'),
        ('MIC_OFF', 'Microphone Turned Off'),
        ('FULLSCREEN_EXIT', 'Exited Fullscreen'),
        ('COPY_PASTE', 'Copy/Paste Detected'),
        ('MULTIPLE_FACES', 'Multiple Faces Detected'),
        ('NO_FACE', 'No Face Detected'),
    ]
    
    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='cheating_logs')
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)  # Additional context
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.session.candidate_name} - {self.event_type} at {self.timestamp}"


class Question(models.Model):
    CATEGORY_CHOICES = [
        ('PERSONAL', 'Personal'),
        ('RESUME', 'Resume-based'),
        ('TECHNICAL', 'Technical'),
        ('CODING', 'Coding Logic'),
        ('BEHAVIORAL', 'Behavioral'),
    ]
    
    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    asked_at = models.DateTimeField(auto_now_add=True)
    
    # Response
    answer_text = models.TextField(blank=True)
    answer_received_at = models.DateTimeField(null=True, blank=True)
    
    # Evaluation
    score = models.FloatField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    
    class Meta:
        ordering = ['asked_at']
    
    def __str__(self):
        return f"Q: {self.question_text[:50]}..."