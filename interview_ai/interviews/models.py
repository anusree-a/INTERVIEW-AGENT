from django.db import models
import uuid

class InterviewSession(models.Model):
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    candidate_name = models.CharField(max_length=100)
    email = models.EmailField()
    resume = models.FileField(upload_to="resumes/", null=True, blank=True)

    status = models.CharField(max_length=20, default="CREATED")

    transcript = models.TextField(blank=True)
    cheating_events = models.JSONField(default=list, blank=True)
    score = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.candidate_name} - {self.status}"
